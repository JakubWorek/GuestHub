import {useParams} from "react-router-dom";
import {useEffect, useState} from "react";
import axios from "axios";
import AddressLink from "../AddressLink";
import PlaceGallery from "../PlaceGallery";
import BookingDates from "../BookingDates";
import 'add-to-calendar-button';
import axiosInstanceWithAuth from "../axiosInstanceWithAuth";

export default function BookingPage() {
  const {id} = useParams();
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    if (id) {
      axiosInstanceWithAuth.get('/bookings').then(response => {
        const foundBooking = response.data.find(({_id}) => _id === id);
        if (foundBooking) {
          setBooking(foundBooking);
        }
      });
    }
  }, [id]);

  if (!booking) {
    return '';
  }

  const bookingStartDate = new Date(booking.checkIn);
  const bookingEndDate = new Date(booking.checkOut);

  // Function to format date to YYYY-MM-DD format
  const formatDate = (date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0'); // Month is zero-based
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  // Format start date and end date
  const formattedStartDate = formatDate(bookingStartDate);
  const formattedEndDate = formatDate(bookingEndDate);

  const bookingStartTime = booking.place.checkIn;
  const bookingEndTime = booking.place.checkOut;

  // Function to format time to hh:mm format
  const formatTime = (time) => {
    const hours = time
    const minutes = 0
    const formattedHours = String(hours).padStart(2, '0'); // Add leading zero if single digit
    const formattedMinutes = String(minutes).padStart(2, '0'); // Add leading zero if single digit
    return `${formattedHours}:${formattedMinutes}`;
  };

  // Format start time and end time
  const formattedStartTime = formatTime(bookingStartTime);
  const formattedEndTime = formatTime(bookingEndTime);

  return (
    <div className="my-8">
      <h1 className="text-3xl">{booking.place.title}</h1>
      <AddressLink className="my-2 block">{booking.place.address}</AddressLink>
      <div className="bg-gray-200 p-6 my-6 rounded-2xl flex items-center justify-between">
        <div>
          <h2 className="text-2xl mb-4">Your booking information:</h2>
          <BookingDates booking={booking} />
        </div>
        <div className="bg-primary p-6 text-white rounded-2xl">
          <div>Total price</div>
          <div className="text-3xl">${booking.price}</div>
        </div>
      </div>
      <PlaceGallery place={booking.place} />
      <div className="mt-4 border-black mb-4">
        <add-to-calendar-button
          name = {booking.place.title}
          description= {booking.place.description}
          startDate= {formattedStartDate}
          endDate= {formattedEndDate}
          startTime = {formattedStartTime}
          endTime= {formattedEndTime}
          location = {booking.place.address}
          options="['Apple','Google','iCal','Microsoft365','Outlook.com','Yahoo']"
          timeZone="Europe/Berlin"
          trigger="click"
          inline
          listStyle="modal"
          iCalFileName="Reminder-Event"
        />
      </div>
    </div>
  );
}