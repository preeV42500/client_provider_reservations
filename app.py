import pathlib
from flask import abort, jsonify, Flask, request 
from datetime import datetime, timezone, timedelta  

from sqlalchemy import or_, and_, func
from flask_sqlalchemy import SQLAlchemy

#app = connexion.App(__name__, specification_dir="./")
#app.add_api("swagger.yml")

basedir = pathlib.Path(__file__).parent.resolve()
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{basedir/'reservations.db'}"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

##################################
# Db models 

class Provider(db.Model):
    __tablename__ = "provider"
    id = db.Column(db.Integer, primary_key=True)
    npi = db.Column(db.BigInteger, nullable=False)
    firstname = db.Column(db.VARCHAR, nullable=False)
    lastname = db.Column(db.VARCHAR, nullable=False)
    available_on = db.Column(db.Date)

    def as_dict(self):
        return {
            'id': self.id,
            'npi': self.npi,
            'firstname': self.firstname,
            'lastname': self.lastname,
            'available_on': self.available_on.strftime(("%Y-%m-%d"))
        }

class AppointmentSlot(db.Model):
    __tablename__ = "appointment_slots"
    id = db.Column(db.Integer, primary_key=True)
    start_time = db.Column(db.DateTime, nullable=False)
    date = db.Column(db.Date, nullable=False)
    provider_id = db.Column(db.Integer, db.ForeignKey('provider.id'), nullable=False)
    reserved_at=db.Column(db.DateTime)
    confirmed_at=db.Column(db.DateTime)

    def as_dict(self):
        return {
            'id': self.id,
            'start_time': self.start_time.strftime(("%Y-%m-%d %H:%M:%S")),
            'date': self.date.strftime(("%Y-%m-%d")),
            'provider_id': self.provider_id,
            'reserved_at': self.reserved_at.strftime(("%Y-%m-%d %H:%M:%S")) if self.reserved_at else None,
            'confirmed_at': self.confirmed_at.strftime(("%Y-%m-%d %H:%M:%S")) if self.confirmed_at else None
        }
    
#######################################   
# Helper function to generate a list of 15-minute appointment slots between start_time and end_time 
def create_timeslots_helper(date, start_time, end_time):

    # combine date and time objects into datetime 
    start_datetime = datetime.combine(date, datetime.strptime(start_time, '%I:%M %p').time())
    end_datetime = datetime.combine(date, datetime.strptime(end_time, '%I:%M %p').time())
    

    total_seconds = int((end_datetime - start_datetime).total_seconds()) 
    interval = int(timedelta(minutes=15).total_seconds())  

    available_slots = []  

    # generate datetimes in 15 minute intervals between start datetime and end
    for i in range(0, total_seconds, interval): 
        time_slot = start_datetime + timedelta(seconds=i) 
        available_slots.append(time_slot)

    return available_slots

def create_appointment_slots(date, start_time, end_time, provider_id): 
    list_of_timeslots = create_timeslots_helper(date, start_time, end_time) 
    appointment_slots = [
        AppointmentSlot(
            start_time=timeslot,
            date = date,
            provider_id=provider_id
        ) for timeslot in list_of_timeslots] 
    return appointment_slots    
    


##### Routes ###########
@app.route('/provider-availability', methods=['POST'])
def post_availability():
    data = request.get_json()
    npi = data['npi'] 
    firstname = data['firstname']
    lastname = data['lastname']
    availablilities = data['availability']
    date = datetime.strptime(data['availability'][0]['date'], '%Y-%m-%d').date()

    # if provider hasn't already submitted availability for that date, 
    # create provider availability record and create corresponding  
    # appointment slots for that date 

    for availablility in availablilities:
        date = datetime.strptime(availablility['date'], '%Y-%m-%d').date()
        start_time = availablility['start_time']
        end_time = availablility['end_time']

        existing_provider = Provider.query\
            .filter(Provider.firstname == firstname, Provider.lastname == lastname, Provider.available_on == date).\
            one_or_none()  

        if not existing_provider: 
            provider = Provider(
                npi=npi, 
                firstname=firstname, 
                lastname=lastname,
                available_on=date  
            )
            db.session.add(provider)
            db.session.flush()
            db.session.add_all(create_appointment_slots(date, start_time, end_time, provider.id))


            db.session.commit()  
    if existing_provider:
        return jsonify(existing_provider.as_dict()), 201 
    else: 
        return jsonify(provider.as_dict()), 201


@app.route('/timeslots', methods=['GET'])
def get_appointment_slots(): 
    firstname = request.args.get('firstname')
    lastname = request.args.get('lastname')
    date = request.args.get('date')
    date_object_local = datetime.strptime(date, '%Y-%m-%d') if date else None
        
    curr_datetime = datetime.now()

    # the appointment is available if it hasn't been reserved 
    # or if the reservation is more than 30 minutes ago and it hasn't been confirmed
    query = AppointmentSlot.query.join(Provider).filter(
    and_(
        AppointmentSlot.date > curr_datetime.date(),
        or_(
            AppointmentSlot.reserved_at.is_(None),
            and_(
                curr_datetime > func.datetime(
                    AppointmentSlot.reserved_at + timedelta(minutes=30)
                ),
                AppointmentSlot.confirmed_at.is_(None),
            ),
        ),
    )
    )

    if firstname:
        query = query.filter(Provider.firstname == firstname)

    if lastname:
        query = query.filter(Provider.lastname == lastname)

    if date and date_object_local > curr_datetime.date():
        query = query.filter(AppointmentSlot.date == date_object_local)

    available_appointments = query.all()
 
    result = [appointment.as_dict() for appointment in available_appointments]

    return jsonify(result)

   
@app.route('/timeslots/reserve', methods=['POST'])
def reserve_appointment():
    data = request.get_json()
    date = data['date']
    date_obj = datetime.strptime(date, '%Y-%m-%d').date()
    provider_npi = data['provider_npi']
    reserved_slot = data['reserved_slot']
    time_obj = datetime.strptime(reserved_slot, '%I:%M %p').time()

    reservation_datetime = datetime.combine(date_obj, time_obj)

    # Query to filter appointments for a specific provider where start_time is at least 24 hours from now
    appointment_slot = db.session.query(AppointmentSlot)\
        .join(Provider)\
        .filter(
            Provider.npi == provider_npi,
            AppointmentSlot.provider_id == Provider.id,
            AppointmentSlot.start_time == reservation_datetime,
            AppointmentSlot.start_time >= datetime.now() + timedelta(hours=24),
    ).one_or_none() 

    if appointment_slot: 
        appointment_slot.reserved_at = datetime.now()  
        db.session.commit() 

        return jsonify({'message': 'Successfully reserved appointment slot'}), 200 
    else: 
        return jsonify({'messsage': 'Appointment timeslot must be at least 24 hours from now'}), 404


@app.route('/timeslots/confirm', methods=['POST'])
def confirm_reservation():
    data = request.get_json()

    date = data['date']
    provider_npi = data['provider_npi']
    reserved_slot = data['reserved_slot']

    reserved_datetime = datetime.strptime(reserved_slot, '%Y-%m-%d %I:%M %p')

    appointment_slot = db.session.query(AppointmentSlot)\
    .join(Provider)\
    .filter(
        Provider.npi == provider_npi,
        AppointmentSlot.provider_id == Provider.id,
        AppointmentSlot.reserved_at == reserved_datetime,
        AppointmentSlot.reserved_at + timedelta(minutes=30) >= datetime.now(),
    ).one_or_none() 

    if appointment_slot: 
        appointment_slot.confirmed_at = datetime.now()  
        db.session.commit() 

        return jsonify({'message': 'Success! You have confirmed your appointment'}), 200 
    else: 
        return jsonify({'messsage': 'Your reservation has expired. Please reserve the timeslot again.'}), 404



if __name__ == '__main__':
    app.run(debug=True)
    # app.run(host="0.0.0.0", port=8000, debug=True)