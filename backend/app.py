import mongoengine
from flask import Flask, jsonify, request,make_response
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from flask_cors import CORS
import os
from werkzeug.utils import secure_filename
from datetime import timedelta
from mongoengine import connect, ValidationError, NotUniqueError,DoesNotExist,Document
from dotenv import load_dotenv
import requests
import shutil
import time
from werkzeug.datastructures import FileStorage
from flask import Flask, jsonify, request
from flask_wtf import FlaskForm
from wtforms import FileField
from flask_wtf.file import FileRequired
from werkzeug.utils import secure_filename
import datetime
import json
from flask_mail import Mail, Message


from mongoengine import Document, StringField, EmailField, ReferenceField, ListField, DateTimeField, FloatField, IntField

import logging #register
# Ładowanie zmiennych środowiskowych z pliku .env
load_dotenv()

# Inicjalizacja aplikacji Flask
app = Flask(__name__)

# Konfiguracja JWT
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=1)

# Konfiguracja i inicjalizacja maila
app.config['MAIL_SERVER'] = 'smtp.fastmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = 'guesthubnotify@fastmail.com'
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
mail = Mail(app)

# Konfiguracja MongoEngine do połączenia z MongoDB
app.config['MONGODB_SETTINGS'] = {
    'db': 'your_database_name',
    'host': os.getenv('MONGO_URI'),
    'connect': False
}

# Inicjalizacja MongoEngine
db = connect(**app.config['MONGODB_SETTINGS'])

# Inicjalizacja Bcrypt i JWT
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
CORS(app, supports_credentials=True)

app.config['SECRET_KEY'] = "siema"
app.config['UPLOAD_FOLDER'] = '/tmp'

# Konfiguracja logowania
logging.basicConfig(level=logging.INFO)

class User(Document):
    name = StringField(required=True)
    email = EmailField(unique=True, required=True)
    password = StringField(required=True)

class Place(Document):
    owner = ReferenceField(User, required=True)
    title = StringField(required=True)
    address = StringField(required=True)
    photos = ListField(StringField())
    description = StringField()
    perks = ListField(StringField())
    extraInfo = StringField()
    checkIn = IntField(required=True)
    checkOut = IntField(required=True)
    maxGuests = IntField(required=True)
    price = FloatField(required=True)

class Booking(Document):
    place = ReferenceField(Place, required=True, reverse_delete_rule=mongoengine.PULL)
    user = ReferenceField(User, required=True)
    checkIn = DateTimeField(required=True)
    checkOut = DateTimeField(required=True)
    name = StringField(required=True)
    phone = StringField(required=True)
    price = FloatField(required=True)
    numberOfGuests = IntField(required=True)

    @classmethod
    def find_by_user(cls, user_id):
        # Utilizing a custom class method to encapsulate query logic
        return cls.objects(user=user_id).select_related()


@app.route('/test/user', methods=['POST'])
def create_user():
    try:
        # Pobranie danych z żądania
        name = request.json['name']
        email = request.json['email']
        password = request.json['password']

        # Tworzenie nowego użytkownika
        user = User(name=name, email=email, password=password)
        user.save()  # Zapis do bazy danych

        # Zwracanie danych użytkownika (bez hasła dla bezpieczeństwa)
        return jsonify({
            'name': user.name,
            'email': user.email
        }), 200
    except Exception as e: # jest to tylko kod sprawdzający czy coś wgl działa, więc łapanie tu konkretnych błędów jest niepotrzebne
        return jsonify({'error': str(e)}), 400

@app.route('/api/register', methods=['POST'])
def register_user():
    try:
        # Pobieranie danych z żądania
        name = request.json.get('name')
        email = request.json.get('email')
        password = request.json.get('password')

        # Hashowanie hasła
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Tworzenie nowego użytkownika
        user = User(name=name, email=email, password=hashed_password)
        user.save()  # Zapis do bazy danych

        # Zwracanie danych użytkownika (bez hasła dla bezpieczeństwa)
        return jsonify({
            'name': user.name,
            'email': user.email
        }), 201

    except ValidationError as ve:
        # Obsługa błędów walidacji (np. brakujące pola)
        logging.error(f"Validation error: {ve}")
        return jsonify({'error': str(ve)}), 400
    except NotUniqueError:
        # Obsługa próby stworzenia użytkownika z już istniejącym adresem email
        logging.error("Attempt to create a user with a duplicate email")
        return jsonify({'error': 'This email is already used.'}), 400
    except Exception as e:
        # Ogólna obsługa błędów
        logging.error(f"Unexpected error: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        email = request.json.get('email')
        password = request.json.get('password')

        user = User.objects.get(email=email)  # Użyj get zamiast first dla lepszej obsługi błędów

        if bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id), additional_claims={"email": user.email})
            response = jsonify(name=user.name, email=user.email, token = access_token)
            #response.set_cookie('token', access_token)
            return response
        else:
            return jsonify({"error": "Invalid credentials"}), 401  # Niepoprawne dane logowania
    except DoesNotExist:
        return jsonify({"error": "User not found"}), 404  # Użytkownik nie istnieje
    except ValidationError:
        return jsonify({"error": "Invalid data"}), 400  # Nieprawidłowe dane wejściowe
    except Exception as e:
        return jsonify({"error": str(e)}), 500  # Inny błąd serwera

@app.route('/api/profile', methods=['GET'])
@jwt_required()  # Wymaga dostarczenia ważnego tokenu JWT w nagłówkach żądania
def get_user_profile():
    try:
        user_id = get_jwt_identity()  # Pobiera identyfikator użytkownika z tokenu JWT
        user = User.objects.get(id=user_id)  # Użyj get dla precyzyjnego odnalezienia i błędu, gdy użytkownik nie istnieje

        # Zwróć dane użytkownika w formacie JSON
        return jsonify({
            "name": user.name,
            "email": user.email,
            "_id": str(user.id)  # Konwersja ObjectId na string
        })

    except DoesNotExist:
        return jsonify({"error": "User not found"}), 404  # Użytkownik nie istnieje
    except ValidationError:
        return jsonify({"error": "Invalid data"}), 400  # Nieprawidłowe dane wejściowe
    except Exception as e:
        # Logowanie błędu dla dalszej analizy
        app.logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "Internal server error"}), 500  # Inny błąd serwera

@app.route('/api/logout', methods=['POST'])
def logout():
    # Tworzenie odpowiedzi, która usunie ciasteczko 'token'
    response = make_response(jsonify(True))  # Zwracamy JSON z wartością True
    response.set_cookie('token', '', expires=0)  # Usuwanie ciasteczka przez ustawienie daty wygaśnięcia na 0
    return response

@app.route('/api/notify', methods=['POST'])
@jwt_required()
def send_email():
    try:
        user_id = get_jwt_identity()
        user = User.objects.get(id=user_id)
        user_email = user.email
        message = request.json.get('message')
        print(user_email)
        print(message)

        msg = Message(  subject = 'GuestHub Notification', 
                        sender='guesthubnotify@fastmail.com',
                        recipients=[user_email],
                        body=message)
        
        mail.send(msg)
        return jsonify('Email sent'), 200
    
    except DoesNotExist:
        return jsonify({"error": "User not found"}), 404  # Użytkownik nie istnieje
    except ValidationError:
        return jsonify({"error": "Invalid data"}), 400 # Nieprawidłowe dane wejściowe
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Inny błąd serwera

@app.route('/api/places', methods=['POST'])
@jwt_required()
def add_place():
    user_id = get_jwt_identity()  # Pobiera identyfikator użytkownika z tokenu JWT
    data = request.json

    place = Place(
        owner=user_id,
        title=data['title'],
        address=data['address'],
        photos=data.get('addedPhotos', []),
        description=data['description'],
        perks=data.get('perks', []),
        extraInfo=data.get('extraInfo', ''),
        checkIn=data['checkIn'],
        checkOut=data['checkOut'],
        maxGuests=data['maxGuests'],
        price=data['price']
    )
    place.save()
    return jsonify(place=place.to_json())

@app.route('/api/user-places', methods=['GET'])
@jwt_required()
def get_user_places():
    user_id = get_jwt_identity()
    places = Place.objects(owner=user_id).all()  # Znajdowanie miejsc należących do użytkownika
    json_data = places.to_json()
    dicts = json.loads(json_data)
    for i in range(len(dicts)):
        dicts[i]['_id'] = dicts[i]['_id']['$oid']
    return dicts

@app.route('/api/places/<id>', methods=['GET'])
def get_place(id): #jedyne nie przetestowane
    try:
        place = Place.objects.get(id=id)
        print(place)
        json_data = place.to_json()
        print(json_data)
        dicts = json.loads(json_data)
        print(dicts)
        dicts['_id'] = dicts['_id']['$oid']
        print(dicts)
        return dicts, 200
    except DoesNotExist:
        return jsonify({"error": "Place not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/places', methods=['PUT'])
@jwt_required()
def update_place():
    user_id = get_jwt_identity()
    data = request.json
    try:
        place = Place.objects.get(id=data['id'])
        if str(place.owner.id) == user_id:
            place.update(
                title=data.get('title', place.title),
                address=data.get('address', place.address),
                photos=data.get('addedPhotos', place.photos),
                description=data.get('description', place.description),
                perks=data.get('perks', place.perks),
                extraInfo=data.get('extraInfo', place.extraInfo),
                checkIn=data.get('checkIn', place.checkIn),
                checkOut=data.get('checkOut', place.checkOut),
                maxGuests=data.get('maxGuests', place.maxGuests),
                price=data.get('price', place.price)
            )
            return jsonify('ok'), 200
        else:
            return jsonify({'error': 'Unauthorized access'}), 403
    except Place.DoesNotExist:
        return jsonify({'error': 'Place not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/places', methods=['GET'])
def get_places():
    places = Place.objects().all()  # Retrieve all documents in the Place collection
    json_data = places.to_json()
    dicts = json.loads(json_data)
    for i in range(len(dicts)):
        dicts[i]['_id'] = dicts[i]['_id']['$oid']
    return dicts, 200
    #return jsonify([place.to_json() for place in places]), 200

@app.route('/api/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    user_id = get_jwt_identity()
    data = request.get_json()
    place_id = data['place']
    checkIn = datetime.datetime.strptime(data['checkIn'], '%Y-%m-%d')
    checkOut = datetime.datetime.strptime(data['checkOut'], '%Y-%m-%d')
    numberOfGuests = int(data['numberOfGuests'])

    try:
        place = Place.objects.get(id=place_id)
        if place.maxGuests < numberOfGuests:
            return jsonify('too many guests'), 422

        overlapping_bookings = Booking.objects(
            place=place_id,
            checkIn__lte=checkOut,
            checkOut__gte=checkIn
        )
        if overlapping_bookings:
            return jsonify('place is not available'), 422

        booking = Booking(
            place=place,
            checkIn=checkIn,
            checkOut=checkOut,
            numberOfGuests=numberOfGuests,
            name=data['name'],
            phone=data['phone'],
            price=data['price'],
            user=user_id
        )
        booking.save()

        dict = json.loads(booking.to_json())
        dict['_id'] = dict['_id']['$oid']
        dict['place'] = dict['place']['$oid']
        dict['user'] = dict['user']['$oid']
        dict['checkIn'] = dict['checkIn']['$date']
        dict['checkOut'] = dict['checkOut']['$date']
        dict['place'] = json.loads(Place.objects().get(id=dict['place']).to_json())
        dict['user'] = json.loads(User.objects().get(id=dict['user']).to_json())

        return dict, 201

    except DoesNotExist:
        return jsonify({'error': 'Place not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    try:
        user_id = get_jwt_identity()
        bookings = Booking.objects(user=user_id).all()
        json_data = bookings.to_json()
        dicts = json.loads(json_data)
        #print(dicts)
        for i in range(len(dicts)):
            dicts[i]['_id'] = dicts[i]['_id']['$oid']
            dicts[i]['place'] = dicts[i]['place']['$oid']
            dicts[i]['user'] = dicts[i]['user']['$oid']
            dicts[i]['checkIn'] = dicts[i]['checkIn']['$date']
            dicts[i]['checkOut'] = dicts[i]['checkOut']['$date']
            # for place in dicts[i]['place'] fetch the place data and for user fetch the user data
            dicts[i]['place'] = json.loads(Place.objects().get(id=dicts[i]['place']).to_json())
            dicts[i]['user'] = json.loads(User.objects().get(id=dicts[i]['user']).to_json())
        #print(dicts)
        return dicts
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(port= 5000,debug=True)