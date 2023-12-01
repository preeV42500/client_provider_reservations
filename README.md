## Dependencies
Install Flask and Flask-SQLAlchemy 

## To run the server
- Start the Flask server by running `python3 app.py` 

## Assumptions

- I am using SQLite for my database, so when datetime data is returned from the database, it will be the local time of the system where the database is located. A future improvement would be to use UTC conversions.
- For simplicity's sake, providers can only submit their availability once for a specific date.

## API Documentation

### POST /provider-availability

#### Request Body Example Format


{
  "firstname": "First",
  "lastname": "Last",
  "npi": "1234567890",
  "availability": [
    {
      "start_time": "8:00 AM",
      "end_time": "3:00 PM",
      "date": "2024-01-02"
    }
  ]
}

### POST /timeslots/reserve

#### Request Body Example Format
{
  "date": "2023-12-03",
  "provider_npi": "1234567890",
  "reserved_slot": "8:15 AM"
}

### POST /timeslots/confirm

#### Request Body Example Format
{
  "date": "2023-12-03",
  "provider_npi": "1234567890",
  "reserved_slot": "2023-12-03 8:15 AM"
}
