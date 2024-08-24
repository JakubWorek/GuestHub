# GuestHub
1) Jakub Białecki, Przemysław Popowski, Jakub Worek
2) Aplikacja 'GuestHub', czyli klon Airbnb - aplikacji do udostępniania swoich pokoi
3) MongoDB, backend stworzony z pomoca Flaska


# Jak uruchomić projekt?
Aby poprawnie uruchomić aplikacje należy:  
1. Otworzyć w terminalu folder upload_service
2. Wykonać polecenie `npm install`
3. Wykonać polecenie `node index.js`
4. Otworzyć w terminalu folder backend
5. Zainstalować wymagane biblioteki Pythona
6. Uruchomić `app.py`
7. Otworzyć w terminalu folder frontend
8. Wykonać polecenie `npm install`
9. Wykonać polecenie `npm run dev`  

I można cieszyć się działającą aplikacją pod linkiem `http://localhost:5173` :D

# Komentarz na wstępie:
Aplikacja została zaprojektowana z myślą o modularności i łatwej skalowalności. 
Użycie MongoDB z ORM MongoEngine ułatwia pracę z danymi, a Flask wraz z rozszerzeniami takimi jak Flask-JWT-Extended i Flask-Bcrypt zapewniają solidne podstawy bezpieczeństwa.

# Model danych - projekt bazy danych:
1. Model "User" - użytkownik
- `name` - imię i nazwisko użytkownika - string
- `email` - email do logowania - email, unique
- `password` - hasło do logowania - string

2. Model "Place" - miejsce oferujące nocleg
- `owner` - referencja do użytkownika będącego właścicielem miejsca - User
- `title` - nazwa miejsca - string
- `address` - adres miejsca - string
- `photos` - zdjęcia miejsca - list[string]
- `description` - opis miejsca - string
- `perks` - lista zalet lub udogodnień oferowanych przez miejsce - list[string]
- `extraInfo` - dodatkowe informacje o miejscu - string
- `checkIn` - godzina meldunku - int
- `checkOut` - godzina wymeldowania - int
- `maxGuests` - maksymalna liczba gości, jaką miejsce może pomieścić - int
- `price` - cena za 1 nocleg - float

3. Model "Booking" - rezerwacja noclegu
- `place` - referencja do miejsca, które zostało zarezerwowane - Place
- `user` - referencja do użytkownika, na którego jest rezerwacja - User
- `checkIn` - data zameldowania - date
- `checkOut` - data wymeldowania - date
- `name` - imię i nazwisko osoby rezerwującej - string
- `phone` - numer telefonu osoby rezerwującej - string
- `price` - zapłacona kwota - float
- `numberOfGuests` - liczba gości podczas noclegu - int

# Opis realizacji operacji w bazie danych:
1. operacja `create_user()` -> stworzenie profilu użytkownika i dodanie go do bazy danych 
```python
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
    except Exception as e: 
        return jsonify({'error': str(e)}), 400
```

2. operacja `register_user()` -> rejestracja nowego użytkownika i dodanie go do bazy danych
```python
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
```

3. operacja `login()` -> logowanie się użytkownika i weryfikacja danych
```python
@app.route('/api/login', methods=['POST'])
def login():
    try:
        # Pobieranie danych z żądania
        email = request.json.get('email')
        password = request.json.get('password')

        # Znalezienie użytkownika o podanym emailu
        user = User.objects.get(email=email)

        # Weryfikacja hasła
        if bcrypt.check_password_hash(user.password, password):
            # Tworzenie ciasteczka 'token'
            access_token = create_access_token(identity=str(user.id), additional_claims={"email": user.email})
            response = jsonify(name=user.name, email=user.email, token = access_token)
            return response
        else:
            # Niepoprawne dane logowania
            return jsonify({"error": "Invalid credentials"}), 401  
    except DoesNotExist:
        # Użytkownik nie istnieje
        return jsonify({"error": "User not found"}), 404
    except ValidationError:
        # Nieprawidłowe dane wejściowe
        return jsonify({"error": "Invalid data"}), 400
    except Exception as e:
        # Inny błąd serwera
        return jsonify({"error": str(e)}), 500
```

4. operacja `get_user_profile()` -> zwraca profil aktualnie zalogowanego użytkownika
```python
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
```

5. operacja `logout()` -> wylogowanie się aktualnie zalogowanego użytkownika
```python
@app.route('/api/logout', methods=['POST'])
def logout():
    # Tworzenie odpowiedzi, która usunie ciasteczko 'token'
    response = make_response(jsonify(True))  # Zwracamy JSON z wartością True
    response.set_cookie('token', '', expires=0)  # Usuwanie ciasteczka przez ustawienie daty wygaśnięcia na 0
    return response
```

6. operacja `send_email()` -> wysłanie emaila użytkownikowi z potwierdzeniem dokonania rezerwacji
```python
@app.route('/api/notify', methods=['POST'])
@jwt_required()
def send_email():
    try:
        # Pobieranie danych z żądania
        user_id = get_jwt_identity()
        user = User.objects.get(id=user_id)
        user_email = user.email
        message = request.json.get('message')

        # Utworzenie struktury wiadomości
        msg = Message(  subject = 'GuestHub Notification', 
                        sender='guesthubnotify@fastmail.com',
                        recipients=[user_email],
                        body=message)

        # Wysłanie emaila
        mail.send(msg)
        return jsonify('Email sent'), 200
    
    except DoesNotExist:
        return jsonify({"error": "User not found"}), 404  # Użytkownik nie istnieje
    except ValidationError:
        return jsonify({"error": "Invalid data"}), 400 # Nieprawidłowe dane wejściowe
    except Exception as e:
        return jsonify({"error": str(e)}), 500 # Inny błąd serwera
```

7. operacja `add_place()` -> dodanie nowego miejsca 
```python
@app.route('/api/places', methods=['POST'])
@jwt_required()
def add_place():
    user_id = get_jwt_identity()  # Pobiera identyfikator użytkownika z tokenu JWT
    data = request.json

    # Utworznie struktury miejsca
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
    # Zapisanie jej w bazie danych
    place.save()
    return jsonify(place=place.to_json())
```

8. operacja `get_user_places()` -> wyświetla miejsca posiadane przez aktualnie zalogowanego użytkownika
```python
@app.route('/api/user-places', methods=['GET'])
@jwt_required()
def get_user_places():
    # Pobiera identyfikator użytkownika z tokenu JWT
    user_id = get_jwt_identity()

    # Znajdowanie miejsc należących do użytkownika
    places = Place.objects(owner=user_id).all()  
    json_data = places.to_json()
    dicts = json.loads(json_data)
    for i in range(len(dicts)):
        dicts[i]['_id'] = dicts[i]['_id']['$oid']
    return dicts
```

9. operacja `get_place(id)` -> zwraca miejsce o podanym ID
```python
@app.route('/api/places/<id>', methods=['GET'])
def get_place(id): 
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

```

10. operacja `update_place()` -> aktualizuje dane o aktualnie edytowanym miejscu
```python
@app.route('/api/places', methods=['PUT'])
@jwt_required()
def update_place():
    # Pobiera identyfikator użytkownika z tokenu JWT
    user_id = get_jwt_identity()
    data = request.json
    try:
        # Aktualizacja danych aktualnego miejsca
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
```

11. operacja `get_places()` -> zwraca wszystkie dostępne miejsca
```python
@app.route('/api/places', methods=['GET'])
def get_places():
    places = Place.objects().all()  # Retrieve all documents in the Place collection
    json_data = places.to_json()
    dicts = json.loads(json_data)
    for i in range(len(dicts)):
        dicts[i]['_id'] = dicts[i]['_id']['$oid']
    return dicts, 200
```

12. operacja `create_booking()` -> tworzy nową rezerwację oraz dodaje ją do bazy danych
```python
@app.route('/api/bookings', methods=['POST'])
@jwt_required()
def create_booking():
    # Pobiera identyfikator użytkownika z tokenu JWT
    user_id = get_jwt_identity()

    # Pobieranie danych z żądania
    data = request.get_json()
    place_id = data['place']
    checkIn = datetime.datetime.strptime(data['checkIn'], '%Y-%m-%d')
    checkOut = datetime.datetime.strptime(data['checkOut'], '%Y-%m-%d')
    numberOfGuests = int(data['numberOfGuests'])

    try:
        # Weryfikacja dostępności noclegu w wybranym miejscu
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

        # Utworzenie rezerwacji i dodanie jej do bazy danych
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
```

13. operacja `get_bookings()` -> zwraca listę rezerwacji aktualnego użytkownika 
```python
@app.route('/api/bookings', methods=['GET'])
@jwt_required()
def get_bookings():
    try:
        # Pobieranie danych z żądania
        user_id = get_jwt_identity()
        bookings = Booking.objects(user=user_id).all()
        json_data = bookings.to_json()
        dicts = json.loads(json_data)

        # Zwrócenie rezerwacji
        for i in range(len(dicts)):
            dicts[i]['_id'] = dicts[i]['_id']['$oid']
            dicts[i]['place'] = dicts[i]['place']['$oid']
            dicts[i]['user'] = dicts[i]['user']['$oid']
            dicts[i]['checkIn'] = dicts[i]['checkIn']['$date']
            dicts[i]['checkOut'] = dicts[i]['checkOut']['$date']
            dicts[i]['place'] = json.loads(Place.objects().get(id=dicts[i]['place']).to_json())
            dicts[i]['user'] = json.loads(User.objects().get(id=dicts[i]['user']).to_json())
        return dicts
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

14. operacja `detailed_bookings()` -> raport szczegółowy o wszystkich rezerwacjach
```python
@app.route('/api/report/detailed_bookings', methods=['GET'])
def detailed_bookings():
    try:
        bookings = Booking.objects().all()
        detailed_report = []

        for booking in bookings:
            user = User.objects.get(id=booking.user.id)
            place = Place.objects.get(id=booking.place.id)

            detailed_report.append({
                'booking_id': str(booking.id),
                'user': {
                    'name': user.name,
                    'email': user.email
                },
                'place': {
                    'title': place.title,
                    'address': place.address
                },
                'check_in': booking.checkIn,
                'check_out': booking.checkOut,
                'price': booking.price
            })
        return detailed_report
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

15. operacja `user_activity_report()` -> raport aktywności użytkowników w określonym przedziale czasowym
```python
@app.route('/api/report/user_activity', methods=['GET'])
@jwt_required()
def user_activity_report():
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    activities = []

    bookings = Booking.objects(checkIn__gte=start_date, checkOut__lte=end_date).all()
    for booking in bookings:
        activities.append({
            'user_id': str(booking.user.id),
            'activity': 'booking',
            'date': booking.checkIn
        })

    users = User.objects(registeredOn__gte=start_date, registeredOn__lte=end_date).all()
    for user in users:
        activities.append({
            'user_id': str(user.id),
            'activity': 'registration',
            'date': user.registeredOn
        })

    users = User.objects(dateOfLogin__gte=start_date, dateOfLogin__lte=end_date).all()
    for user in users:
        activities.append({
            'user_id': str(user.id),
            'activity': 'login',
            'date': user.dateOfLogin
        })

    return activities
```

16. operacja `financial_raport()` -> raport finansowy poszczególnych miejsc z ostatniego roku podzielony na miesiące
```python
@app.route('/api/report/financial', methods=['GET'])
def financial_report():
    year = request.args.get('year')
    monthly_earnings = []

    for month in range(1, 13):
        bookings = Booking.objects(
            checkIn__year=year, checkIn__month=month
        )
        for booking in bookings:
            monthly_earnings.append({
                'month': month,
                'total_earnings': booking.sum('price'),
                'booking_title': booking.booking_title
            })

    return monthly_earnings
```

17. operacja `users_total_spending()` -> raport zwracający sumę wydanych pieniędzy przez poszczególnych użytkowników
```python
@app.route('/api/report/users_total_spending_', methods=['GET'])
def users_total_spending():
    try:
        users = User.objects().all()
        user_total_spending = []
        for user in users:
            bookings_spending = Booking.objects(user_id = user.id).sum('price')
            user_total_spending.append({
                'user_id': user.id,
                'user_email': user.email,
                'bookings_spending':bookings_spending
            })

        return user_activity_report, 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
```

# Demonstracja możliwości technologii wykorzystywanych w projekcie:
1. `Flask`: Służy jako framework webowy do tworzenia i obsługi API.
2. `Flask-Bcrypt`: Użyty do hashowania haseł, aby zapewnić większe bezpieczeństwo użytkowników.
3. `Flask-JWT-Extended`: Do obsługi tokenów JWT, zapewniających bezpieczne uwierzytelnianie i autoryzację.
4. `Flask-CORS`: Umożliwia obsługę CORS (Cross-Origin Resource Sharing), co jest niezbędne dla aplikacji działających na różnych domenach.
5. `MongoEngine`: Służy jako ORM (Object-Relational Mapping) dla MongoDB, umożliwiając wygodniejsze operacje na bazie danych.
6. `Flask-Mail`: Do wysyłania powiadomień emailowych.
7. `dotenv`: Do ładowania zmiennych środowiskowych z pliku .env.

# Dyskusja zastosowanych technik i metod
1. `JWT`: Tokeny JWT zapewniają bezpieczne i skalowalne uwierzytelnianie. Są łatwe do przechowywania po stronie klienta (np. w ciasteczkach lub localStorage).
2. `ORM (MongoEngine)`: ORM ułatwia pracę z bazą danych, pozwalając na operacje CRUD za pomocą obiektów Pythona zamiast bezpośrednich zapytań do bazy danych.
3. `Hashowanie haseł`: Użycie bcrypt do hashowania haseł zapewnia wysoki poziom bezpieczeństwa, chroniąc przed atakami typu brute-force.
