# Project notes for Redwing GCS Web Application

## Requirements as specified by Gaurav in his mail:
* Saves the daily flight data
* Manage deliveries and orders, gives notifications  on order.
* Integrated with an order placement app

## Shell exports
```
export FLASK_APP=app.py
export DATABASE_URL="postgresql://localhost/redwingdb"
export APP_SETTINGS="config.DevelopmentConfig"
```

## Postgres user
```
sudo -u postgres psql redwingdb
```
