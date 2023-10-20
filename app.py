from flask import Flask, render_template, request,redirect,url_for,flash,session,Response
import logging
from pymongo import MongoClient 
from bson.objectid import ObjectId
from datetime import datetime
from dateutil import parser
from functools import wraps
import smtplib
from flask_bcrypt import bcrypt

from email.mime.multipart import MIMEMultipart

from email.mime.text import MIMEText

# seats
# start_date=datetime.date.today()
# for i in range(30):




app=Flask(__name__) 



app.secret_key = "hello-"
logging.basicConfig(filename="record1.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
 

handler = logging.FileHandler('app.log')

handler.setLevel(logging.DEBUG)

 

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)
client=MongoClient("mongodb://localhost:27017")
db=client.railways 
'''----------------------------------------------'''

def login_required(f):

    @wraps(f)

    def allow_only_valid(*args, **kwargs):

        if 'name' not in session:

            return redirect(url_for('login'))

        return f(*args, **kwargs)

    return allow_only_valid
'''--'''





'''-----------------------------------------'''
def available_seats_for_date(train_no,input_date):
    try:
        train = db.train.find_one({'train_no': train_no})
        booked_seats = len(train.get('dates_booked_seats', {}).get(input_date, []))
        return train['total_seats'] - booked_seats
    except Exception as e:
        logging.error(f"An error occurred while fetching available seats for date {input_date} of train {train_no}: {str(e)}")
        return None

def find_next_available_seat(train_no, date):
    # Find the train document for the specified train_no
    try:
        train = db.train.find_one({'train_no': train_no})

        if train:
            # Extract booked_seats for the specific date or initialize with an empty list
            booked_seats = train.get('dates_booked_seats', {}).get(date, [])

            total_seats = train['total_seats']

            if len(booked_seats) < total_seats:
                # Find the next available seat number (increment by 1)
                next_available_seat_number = len(booked_seats) + 1
                return next_available_seat_number

        return None  # Indicates that there are no available seats
    except Exception as e:
        logger.error(f"An error occurred while finding next available seat for date {date} of train {train_no}: {str(e)}")
        return None

def book_seat(train_no, date, user_id):
    try:
        next_available_seat = find_next_available_seat(train_no, date)

        if next_available_seat:
            # Assign this seat number to the passenger's booking
            passenger_seat_number = next_available_seat

            # Update the train's booked_seats list for the specific date to mark the assigned seat as booked
            update_field = f'dates_booked_seats.{date}'
            db.train.update_one(
                {'train_no': train_no},
                {"$push": {update_field: passenger_seat_number}}
            )

            # Add the booking information to the booking_history collection
            db.booking_history.insert_one({
                'user_id': ObjectId(user_id),
                'train_no': train_no,
                'date': date,
                'seat_number': passenger_seat_number,
                # Other booking information can be added here if necessary
            })

            return f"Seat {passenger_seat_number} booked successfully for date {date}!"
    
        else:
            return f"No seats available for date {date}!"
    except Exception as e:
        logger.error(f"An error occurred while booking seat for date {date} of train {train_no} for user {user_id}: {str(e)}")
        return None
'''----------------------------------------------------------------------'''
def get_next_seat(train_no,date):
    try:
        train = db.train.find_one({'train_no': train_no})
        booked_seats_for_date = train.get('dates_booked_seats', {}).get(date, [])
        
        if booked_seats_for_date:
            return max(booked_seats_for_date) + 1
        else:
            return 1 
    except Exception as e:
        logger.error(f"An error occurred while getting next seat number for date {date} of train {train_no}: {str(e)}")
        return None

'''--------------------------------------------------------'''
'''------------------------------------------this the sign-up page------------------------------------- '''




@app.route("/signup",methods=('GET','POST'))

def signup():
    try:
        if request.method == 'POST':
            name = request.form['name']
            password = request.form['password']
            email = request.form['email']
            phoneno = request.form['phone']
            user_exists = db.user.find_one({'name': name})
            # hashedPassword = bcrypt.generate_password_hash(password, 10)
            if not user_exists:
                # Add the new user to the database
                db.user.insert_one({'name': name, 'password': password, 'email': email, 'phoneno': phoneno})
                flash('Registration successful! Please log in.', 'success')
                app.logger.info('New user registered: %s', name)
                return redirect(url_for('login'))
            else:
                # The username already exists in the database, display an error message to the user
                flash('Username already taken. Please choose a different username.', 'error')
                app.logger.error('Username already taken: %s', name)
                return render_template('signup.html', error='Username already taken. Please choose a different username.')

        return render_template('signup.html')

    except Exception as e:
        logger.error(f"An error occurred while processing signup request: {str(e)}")
        return render_template('signup.html', error='An error occurred. Please try again later.')




'''------------------------this the login-up page  for both user and admin--------------------------------'''

@app.route("/login", methods=('GET','POST'))

def login():
    try:
        if request.method == 'POST':
            name = request.form['name']
            password = request.form['password']
            # bcrypt.check_password_hash(rec["password"], password)
            role = request.form.get('role')
            session["name"] = name
            if role == 'user':
                user = db.user.find_one({'name': name, 'password': password})
                if user:
                    session['user_id'] = str(user['_id'])
                    session['theme'] = 'light'
                    print("J")
                    bookings = db.booking_history.find({'user_id': ObjectId(session['user_id'])})
                    return redirect(url_for('booking_history'))
                else:
                    flash('Invalid username or password', 'error')
                    app.logger.error('Invalid username or password: %s %s', name, password)
                    return render_template("login.html", error="Invalid username or password. Please try again.")
            elif role == 'admin':
                admin = db.admin.find_one({'name': name, 'password': password})
                if admin:
                    session['theme'] = 'light'
                    print(session["name"])
                    return redirect (url_for('trains_dash'))
                    
                   
                else:
                    flash('Invalid username or password', 'error')
                    app.logger.error('Invalid username or password: %s %s', name, password)
                    return render_template("login.html", error="Invalid username or password. Please try again.")
            else:
                flash('Invalid role selected', 'error')
                app.logger.error('Invalid role selected')
                return render_template("login.html", error="Invalid role selected.")

        return render_template("login.html", error=None)

    except Exception as e:
        logger.error(f"An error occurred while processing login request: {str(e)}")
        return render_template("login.html", error="An error occurred. Please try again later.")
  


'''-----------------------------------this code is testing purpose for the admin------------------------------------'''

# @app.route("/admin-login",methods=('GET','POST'))
# def admin_login():
#     if request.method=='POST':
#         name=request.form['name']
#         password=request.form['password']
#         admin=db.admin.find_one({'name':name,'password':password})
#         if admin:
#             return redirect (url_for('trains_dash'))

#     return render_template("admin_login.html")


# The base.html contains navbar which is extended for admin 
@app.route("/base",methods=('GET','POST'))
@login_required
def base():
    try:
        return render_template("base.html")
    except Exception as e:
        logger.error(f"An error occurred while rendering base template: {str(e)}")
        return render_template("error.html", message="An error occurred. Please try again later.")

# -----------------------------------------The trains_dash consists of all the trains ---------------------------


@app.route("/trains_dash", methods=('GET', 'POST'))
@login_required
def trains_dash():
    query = request.args.get('query')
    if query:
        trains = db.train.find({
                "$or": [
                    {"train_no": {"$regex": query, "$options": "i"}},
                    {"source":{"$regex": query, "$options": "i"}},
                    {"destination":{"$regex": query, "$options": "i"}},
                    {"status":{"$regex": query, "$options": "i"}},
                    {"days_of_week":{"$regex": query, "$options": "i"}}
                    
                ]
            })
    else:
        trains = db.train.find({})
        
    return render_template("trains_dash.html", trains=trains)


# --------------------The trains_details consists of details for adding a train-------------------


@app.route("/train_details",methods=('GET','POST'))
@login_required
def train_details():
    if request.method=='POST':
        train_no=request.form['train_no']
        source=request.form['source']
        destination=request.form['destination']
        start_time=request.form['start_time']
        destination_time=request.form['destination_time']
        coaches=request.form['coaches']
        no_of_coaches=int(request.form['no_of_coaches'])
        total_seats=int(request.form['total_seats'])
        fare=int(request.form['fare'])
        days_of_week=request.form.getlist('days_of_week')
        status=request.form.getlist('status')
        

        db.train.insert_one({'train_no':train_no,'source':source,'destination':destination,'start_time':start_time,'destination_time':destination_time,'coaches':coaches,'no_of_coaches':no_of_coaches,'total_seats':total_seats,'fare':fare,'days_of_week':days_of_week,'status':status})
        return redirect(url_for('trains_dash'))
    data=db.train.find()
    return render_template("train_details.html",trains=data)


#---------------------------route to delete a train----------------------------------

@app.post('/<id>/delete/')
@login_required
def delete(id):
    try:
        db.train.delete_one({"_id": ObjectId(id)})
        logger.info('Train deleted: ' + id)
        return redirect(url_for('trains_dash'))

    except Exception as e:
        logger.error('An error occurred while deleting train ' + id + ': ' + str(e))
        return render_template("error.html", error=str(e))
    

#-------------------------------route to update a train  i.e searches train in train collection ------------

@app.post('/<id>/update/')
@login_required
def update(id):
    try:
        data=db.train.find_one({"_id": ObjectId(id)})
        return render_template("train_update.html",train=data)
    except Exception as e:
        logger.error('An error occurred while updating train ' + id + ': ' + str(e))
        return render_template("error.html", error=str(e)) 
#--------------------------------route to modify a train details----------------------------------------

@app.post('/<id>/modify/')
@login_required
def modify(id):
    try:
        train_no=request.form['train_no']
        source=request.form['source']
        destination=request.form['destination']
        start_time=request.form['start_time']
        destination_time=request.form['destination_time']
        coaches=request.form['coaches']
        no_of_coaches=int(request.form['no_of_coaches'])
        total_seats=int(request.form['total_seats'])
        fare=int(request.form['fare'])
        days_of_week=request.form.getlist('days_of_week')
        status=request.form.getlist('status')

        db.train.update_one({'_id':ObjectId(id)},{ '$set': {'train_no':train_no,'source':source,'destination':destination,'start_time':start_time,'destination_time':destination_time,'coaches':coaches,'no_of_coaches':no_of_coaches,'total_seats':total_seats,'fare':fare,'days_of_week':days_of_week,'status':status}})
        data=db.train.find()
        return render_template("trains_dash.html",trains=data)
    except Exception as e:
        logger.error('An error occurred while modifying train ' + id + ': ' + str(e))
        return render_template("error.html", error=str(e))
#------------------------------creating a  route to show history of booked tickets to admin--------------------------

@app.route('/admin_booking_history',methods=('GET','POST'))
@login_required
def admin_booking_history():
    query = request.args.get('query')
    if query:
        # Retrieve bookings based on train number or date
        bookings = db.booking_history.find({
            "$or": [
                {"train_no": {"$regex": query, "$options": "i"}},
                {"source":{"$regex": query, "$options": "i"}},
                {"destination":{"$regex": query, "$options": "i"}},

                {"date": query}
            ]
        })
    else:
        # Retrieve all bookings
        bookings = db.booking_history.find({})
    
    return render_template('admin_booking_history.html', bookings=bookings)
   

'''---------------------------creating user-side routes-------------------------------------------'''

#route to user_dash board 

@app.route("/user_dash",methods=('GET','POST'))
@login_required
def user_dash():
    return render_template("user_dash.html")

'''------------------creating user routes to search for trains----------------------------------'''
@app.route('/find_trains',methods=('GET','POST'))
@login_required
def find_trains():
    source=request.form['source']
    destination=request.form['destination']
    date=request.form['date']   
    current_date=datetime.now().date()
    date_string = date
    date_obj = datetime.strptime(date_string, '%Y-%m-%d')
    days_of_week = str(date_obj.strftime('%A')) 
    print(days_of_week)
    trains=db.train.find({'source':source,'destination':destination,'days_of_week':{ "$in" :[days_of_week]}})
    train_data=[]
    for train in trains:
        train['available_seats']=available_seats_for_date(train["train_no"],date)
        train_data.append(train)


    return render_template("find_trains.html",trains=train_data,date=date,current_date=current_date)
    
'''-------------------------------------------------------------------------------------'''

@app.post('/<id>/<date>/book/')
@login_required
def book(id,date):
    try:
        data = db.train.find_one({"_id": ObjectId(id)})
        booking = db.booking_history.find({"_id": ObjectId(id)})
        return render_template("book_train.html", train=data, date=date, booking_history=booking)
    except Exception as e:
        logger.exception("Exception occurred while booking train: %s", str(e))
        flash('There was an error while booking the train. Please try again later.', 'error')
        return redirect(url_for('user_dash'))

'''---------------------creating user routes to book a train---------------------------------------------'''

@app.route('/booked_history',methods=('GET','POST'))
@login_required
def booked_history():
    try:
        train_no=request.form['train_no']
        source=request.form['source']
        destination=request.form['destination']
        date=request.form['date']
        start_time=request.form['start_time']
        destination_time=request.form['destination_time']
        no_of_seats=int(request.form['no_of_seats'])
        fare_per_passenger=0

        next_seat_number=find_next_available_seat(train_no,date)
        passenger_details=[]
        train=db.train.find_one({'train_no':train_no})

        booked_seats=len(train.get('dates_booked_seats',{}).get(date,[]))
        available_seats=train['total_seats'] - booked_seats


        if available_seats < no_of_seats:
            flash('Not enough seats available','error')
            return redirect(url_for('user_dash'))
    
        start_seat=booked_seats +1
        end_seat=booked_seats+no_of_seats
        seats_booked=list(range(start_seat,end_seat + 1))

        update_field=f'dates_booked_seats.{date}'
        db.train.update_one(
            {'train_no':train_no},
            {"$push":{update_field:{"$each":seats_booked}}}
        )


        fare_per_passenger=train['fare']
        total_fare=fare_per_passenger*no_of_seats

        passenger_details=[]
        for i in range(1,no_of_seats+1):
            next_seat=get_next_seat(train_no,date)
            name=request.form.get(f'name{i}')
            age=int(request.form.get(f'age{i}',0))
            sex=request.form.get(f'sex{i}')
            # passenger_fare=0

            if age <10:
                total_fare-=fare_per_passenger*0.5

            passenger_details.append({
                'name':name,
                'age':age,
                'sex':sex,
                'fare':fare_per_passenger if age >=10 else fare_per_passenger*0.5,
                'seat_number':next_seat_number
            })
            next_seat_number+=1
        logger.info("Passenger details: %s", str(passenger_details))
    # print(passenger_details)
        booking_data={
    'user_id':ObjectId(session['user_id']),
      'train_no': train_no ,
      'source':source,
      'destination':destination,
      'date':date,
      'start_time':start_time,
      'destination_time':destination_time,
      'no_of_seats':no_of_seats,
      'passenger_details':passenger_details,
      'total_fare':total_fare}
        insert_result=db.booking_history.insert_one(booking_data)
        booking_id=insert_result.inserted_id



    # db.train.update_one({'train_no':train_no},{"$inc":{'total_seats':-no_of_seats}})
    # bookings=db.booking_history.find({'user_id':ObjectId(session['user_id'])})

        return render_template("payment_gateway.html",fare=total_fare,booking_id=str(booking_id))

    except Exception as e:
        logger.exception("Exception occurred while fetching booking history: %s", str(e))
        flash('There was an error while fetching your booking history. Please try again later.', 'error')
        return redirect(url_for('user_dash'))

'''------------------creating user routes to show booking of  a train----------------------------'''

@app.route('/booking_history',methods=('GET','POST'))
@login_required
def booking_history():
    try:
        user_id = ObjectId(session['user_id'])
        logger.info("User ID: %s", str(user_id))
        bookings = db.booking_history.find({'user_id': ObjectId(session['user_id'])})
        return render_template('booking_history.html', bookings=bookings)
    except Exception as e:
        logger.exception("Exception occurred while fetching booking history: %s", str(e))
        flash('There was an error while fetching your booking history. Please try again later.', 'error')
        return redirect(url_for('user_dash'))

'''----------------------------creating booking summary --------------------------------------------'''
@app.post('/<booking_id>/booking')
@login_required
def booking_summary(booking_id):
    try:
        user_id = ObjectId(session['user_id'])
        logger.info("User ID: %s", str(user_id))
        booking_data = db.booking_history.find_one({'_id':ObjectId(booking_id)})
        logger.info("Booking data: %s", str(booking_data))
        return render_template('booking_summary.html', booking_data=booking_data)
    except Exception as e:
        logger.exception("Exception occurred while fetching booking summary: %s", str(e))
        flash('There was an error while fetching the booking summary. Please try again later.', 'error')
        return redirect(url_for('user_dash'))
    


'''---------------------------booking payment succes----------------------------------------'''

@app.route('/payment_gateway/<id>')
@login_required
def payment_gateway(id):
    try:
        booking = db.booking_history.find_one({"_id": ObjectId(id)})
        logger.info("Booking ID: %s", str(id))
        return render_template('booking_summary.html', booking_data=booking)
    except Exception as e:
        logger.exception("Exception occurred while fetching booking details: %s", str(e))
        flash('There was an error while fetching the booking details. Please try again later.', 'error')
        return redirect(url_for('user_dash'))




    
'''---------------------------creating a route to delete a ticket by user------------------'''

@app.post('/<id>/<train_no>/<seats>/delete_ticket/')
@login_required
def delete_ticket(id, train_no, seats):
    try:
        booking_data = db.booking_history.find_one({"_id": ObjectId(id)})
        date = booking_data["date"]
        seats_to_remove = [p["seat_number"] for p in booking_data["passenger_details"]]

        # Remove the canceled seats from the train's booked seats for the specific date
        update_field = f'dates_booked_seats.{date}'
        db.train.update_one(
            {'train_no': train_no},
            {"$pullAll": {update_field: seats_to_remove}}
        )

        db.booking_history.delete_one({"_id": ObjectId(id)})
        return redirect(url_for('booking_history'))
    except Exception as e:
        logger.exception("Exception occurred while deleting the ticket: %s", str(e))
        flash('There was an error while deleting the ticket. Please try again later.', 'error')
        return redirect(url_for('user_dash'))
    


# --------------------setting the dark mode option in the website

@app.route('/toggle-theme')

def toggle_theme():
    try:
        
        if session['theme'] == 'light':
            session['theme'] = 'dark'
        else:
            session['theme'] = 'light'
        return redirect(request.referrer)
    except Exception as e:
        logger.exception("Exception occurred while toggling theme: %s", str(e))
        flash('There was an error while setting the theme. Please try again later.', 'error')
        return redirect(url_for('user_dash'))


''''--------------------------------------------------'''

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))
'''--------------------------------------------'''



if __name__=='__main__':
    app.run(debug=True)