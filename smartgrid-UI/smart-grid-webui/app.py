import os
import time
import uuid
import threading
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from services import (
    list_meters,
    create_meter,
    update_meter,
    delete_meter,
    delete_readings_by_meter,
    trigger_simulation,
    get_readings,
    get_averages,
    get_peaks,
    get_categories,
)

# In-memory job store: job_id -> {"status": "running"|"done"|"error", "message": str}
_jobs = {}
_JOB_TTL_SECONDS = 3600


def _prune_jobs():
    """Drop finished jobs older than the TTL so the store can't grow forever."""
    cutoff = time.time() - _JOB_TTL_SECONDS
    stale = [
        job_id
        for job_id, job in _jobs.items()
        if job["status"] != "running" and job.get("finished_at", 0) < cutoff
    ]
    for job_id in stale:
        _jobs.pop(job_id, None)

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "smartgrid-client-secret")

DATASET_START = "2007-01-01"
DATASET_END = "2007-06-30"

def is_valid_dataset_date(date_text):
    if not date_text:
        return True

    try:
        date_value = datetime.strptime(date_text, "%Y-%m-%d").date()
        start = datetime.strptime(DATASET_START, "%Y-%m-%d").date()
        end = datetime.strptime(DATASET_END, "%Y-%m-%d").date()
        return start <= date_value <= end
    except ValueError:
        return False

def dates_are_valid(start_date, end_date):
    if not is_valid_dataset_date(start_date):
        return False

    if not is_valid_dataset_date(end_date):
        return False

    if start_date and end_date:
        return start_date <= end_date

    return True


@app.route("/", methods=["GET"])
def index():
    meters = []
    readings = []
    averages = []
    peaks = None
    categories = None

    selected_meter_id = request.args.get("meter_id", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()
    analysis_type = request.args.get("analysis_type", "").strip()

    try:
        meters = list_meters()
    except Exception as e:
        flash(f"Failed to load meters: {e}", "error")

    if selected_meter_id or start_date or end_date:
        if not dates_are_valid(start_date, end_date):
            flash("Dates must be between 2007-01-01 and 2007-06-30, and start date must be before end date.", "error")
        else:
            try:
                meter_id = int(selected_meter_id) if selected_meter_id else None
                readings = get_readings(
                    meter_id=meter_id,
                    start_date=start_date or None,
                    end_date=end_date or None
                )
            except Exception as e:
                flash(f"Failed to load readings: {e}", "error")

    if analysis_type:
        try:
            if not selected_meter_id or not start_date or not end_date:
                flash("Meter ID, start date, and end date are required for analysis.", "error")
            elif not dates_are_valid(start_date, end_date):
                flash("Analysis dates must be between 2007-01-01 and 2007-06-30, and start date must be before end date.", "error")
            else:
                meter_id = int(selected_meter_id)

                if analysis_type == "averages":
                    averages = get_averages(meter_id, start_date, end_date)
                elif analysis_type == "peaks":
                    peaks = get_peaks(meter_id, start_date, end_date)
                elif analysis_type == "categories":
                    categories = get_categories(meter_id, start_date, end_date)
        except Exception as e:
            flash(f"Failed to load analysis: {e}", "error")

    sim_job = request.args.get("sim_job", "")

    return render_template(
        "index.html",
        meters=meters,
        readings=readings,
        averages=averages,
        peaks=peaks,
        categories=categories,
        selected_meter_id=selected_meter_id,
        start_date=start_date,
        end_date=end_date,
        analysis_type=analysis_type,
        sim_job=sim_job,
    )

@app.route("/meters/create", methods=["POST"])
def meters_create():
    name = request.form.get("name", "").strip()
    if not name:
        flash("Meter name is required.", "error")
        return redirect(url_for("index"))

    try:
        create_meter(name)
        flash("Meter created successfully.", "success")
    except Exception as e:
        flash(f"Failed to create meter: {e}", "error")

    return redirect(url_for("index"))

@app.route("/meters/update", methods=["POST"])
def meters_update():
    meter_id = request.form.get("meter_id", "").strip()
    name = request.form.get("name", "").strip()

    if not meter_id or not name:
        flash("Meter ID and new name are required.", "error")
        return redirect(url_for("index"))

    try:
        update_meter(int(meter_id), name)
        flash("Meter updated successfully.", "success")
    except Exception as e:
        flash(f"Failed to update meter: {e}", "error")

    return redirect(url_for("index"))

@app.route("/meters/delete", methods=["POST"])
def meters_delete():
    meter_id = request.form.get("meter_id", "").strip()

    if not meter_id:
        flash("Meter ID is required.", "error")
        return redirect(url_for("index"))

    try:
        delete_readings_by_meter(int(meter_id))
    except Exception:
        pass  # best-effort; don't block meter deletion if readings cleanup fails

    try:
        delete_meter(int(meter_id))
        flash("Meter deleted successfully.", "success")
    except Exception as e:
        flash(f"Failed to delete meter: {e}", "error")

    return redirect(url_for("index"))

@app.route("/simulate", methods=["POST"])
def simulate():
    meter_id = request.form.get("meter_id", "").strip()
    start_date = request.form.get("start_date", "").strip()
    end_date = request.form.get("end_date", "").strip()

    if not meter_id:
        flash("Meter ID is required for simulation.", "error")
        return redirect(url_for("index"))

    if not dates_are_valid(start_date, end_date):
        flash("Simulation dates must be between 2007-01-01 and 2007-06-30, and start date must be before end date.", "error")
        return redirect(url_for("index"))

    _prune_jobs()
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "running", "message": "Simulation in progress…"}

    def run():
        try:
            trigger_simulation(
                int(meter_id),
                start_date=start_date or None,
                end_date=end_date or None,
            )
            _jobs[job_id] = {
                "status": "done",
                "message": "Simulation completed successfully.",
                "finished_at": time.time(),
            }
        except Exception as e:
            _jobs[job_id] = {
                "status": "error",
                "message": f"Simulation failed: {e}",
                "finished_at": time.time(),
            }

    threading.Thread(target=run, daemon=True).start()
    return redirect(url_for("index", sim_job=job_id))


@app.route("/simulate/status/<job_id>")
def simulate_status(job_id):
    job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404
    return jsonify({"status": job["status"], "message": job["message"]})

if __name__ == "__main__":
    # Debug mode is opt-in via FLASK_DEBUG=1 — never enable it by default.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8004)), debug=os.getenv("FLASK_DEBUG") == "1")