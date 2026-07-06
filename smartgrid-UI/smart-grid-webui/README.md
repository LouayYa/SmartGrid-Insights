# Client Interface Service

A Flask web interface for the Smart Grid microservices project.

This service provides a browser-based interface for:

- Viewing meters
- Creating meters
- Updating meters
- Deleting meters
- Triggering reading simulations
- Viewing readings
- Viewing analysis results such as averages, peaks, and usage categories

This app does not store data directly. It communicates with other backend services through HTTP APIs.

---

## Project Structure

```text
.
├── app.py
├── config.py
├── services.py
├── requirements.txt
├── startup.sh
├── templates/
│   └── index.html
├── static/
│   └── styles.css
├── .env.example
├── .gitignore
└── README.md

Make sure to add these as environment variables:

METER_SERVICE_URL=https://meter-registration-service-ethzdmb2dvanhbft.centralindia-01.azurewebsites.net
COLLECTION_SERVICE_URL=https://smartgrid-data-collection.azurewebsites.net
ANALYSIS_SERVICE_URL=https://smartgrid-data-analysis.azurewebsites.net
SECRET_KEY=change-this-secret-key