from flask import Blueprint, request, jsonify
from sqlalchemy.exc import IntegrityError
from models import db, Meter

meter_bp = Blueprint("meter_bp", __name__)

@meter_bp.route("/meters", methods=["POST"])
def create_meter():
    data = request.get_json() or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400

    existing = Meter.query.filter_by(name=name).first()
    if existing:
        return jsonify({"error": "meter name already exists"}), 409

    meter = Meter(name=name)
    db.session.add(meter)
    try:
        db.session.commit()
    except IntegrityError:
        # Covers the race where the same name is inserted between check and commit.
        db.session.rollback()
        return jsonify({"error": "meter name already exists"}), 409

    return jsonify(meter.to_dict()), 201


@meter_bp.route("/meters", methods=["GET"])
def get_all_meters():
    meters = Meter.query.order_by(Meter.meter_id.asc()).all()
    return jsonify([m.to_dict() for m in meters]), 200


@meter_bp.route("/meters/<int:meter_id>", methods=["GET"])
def get_meter(meter_id):
    meter = db.session.get(Meter, meter_id)
    if not meter:
        return jsonify({"error": "meter not found"}), 404

    return jsonify(meter.to_dict()), 200


@meter_bp.route("/meters/<int:meter_id>", methods=["PUT"])
def update_meter(meter_id):
    meter = db.session.get(Meter, meter_id)
    if not meter:
        return jsonify({"error": "meter not found"}), 404

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()

    if not name:
        return jsonify({"error": "name is required"}), 400

    existing = Meter.query.filter(Meter.name == name, Meter.meter_id != meter_id).first()
    if existing:
        return jsonify({"error": "meter name already exists"}), 409

    meter.name = name
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "meter name already exists"}), 409

    return jsonify({
        "meter_id": meter.meter_id,
        "name": meter.name,
        "status": "updated"
    }), 200


@meter_bp.route("/meters/<int:meter_id>", methods=["DELETE"])
def delete_meter(meter_id):
    meter = db.session.get(Meter, meter_id)
    if not meter:
        return jsonify({"error": "meter not found"}), 404

    db.session.delete(meter)
    db.session.commit()

    return jsonify({
        "meter_id": meter_id,
        "status": "deleted"
    }), 200
    
@meter_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200    