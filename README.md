## Visa Checker

I made this program in 2022 for my girlfriend to automate the process of finding a visa renewal appointment. 
At the time, visa renewal appointment slots were extremely hard to 
come by and the earliest appointments were a couple years out. 
years out. Even more so for populated areas like Toronto and Vancouver.

It was a fun little project even though I knew from the outset that 
it was only going to be used once. I had no plans on turning it into a 
service for others to use because of the sensitive nature of the info 
it had access to.

Recently, I decided to practice some refactoring by turning the 
original 800 line script into what you see here. I haven't verified 
if the script still works (either due to changes in the visa renewal
website or bugs in my refactoring) since I no longer have access to an
account which is in the renewal process. That said, I did at least 
verify that the program can still load. There's probably a few bugs 
here and there but if anyone is determined to get this working again,
it shouldn't be too far off from where it needs to be.

This program was designed for US Visa renewals with appointments 
in Canada. I don't know if the visa site works the same way for 
appointments in other countries. I imagine they probably do.

### Features
- Specify which cities to track (eg. only Toronto and Vancouver)
- Notifications when new appointment slots are detected through [ntfy](https://ntfy.sh/)
- Automatically reschedule new appointments if a preferrable date/location is found. 
    - This ended up being added later and quite useful since we would
    often miss the new slot that opened by the time we were able to log
    on ourselves.
- Handles temporary bans
    - This can happen if too many requests have been sent.
    - I tried tuning the request frequency lower so that we wouldn't get banned
    at all but that ended up reducing the frequency to the point where I felt
    like it would no longer reliably detect new slots. I found the best strategy
    to be to still check for availability at a reasonable rate and then just wait
    for the temporary ban to expire.
- Continues working across multiple authentication sessions
- Handles server downtime

### Implementation Overview
The program is designed to be started once and left running instead of being
executed at regular intervals. There is an in memory job queue which consists
of the cities that we want to check availability for. A job for each city that
we want to check will be be added to the queue at a regular interval.

Playwright is used to run a fake browser session that goes through the login
flow and navigates to the appointment selection page. When a job (city) is 
being processed, a browser action will be performed which triggers a JSON 
response with the availability for the city. The program listens for that JSON 
response and then handles the response by comparing the current availability 
with the previously known availability for that city. If any new slots are 
found, a notification will be sent out. If any of those slots are a "preferred"
slot, the program will also execute a rescheduling workflow to confirm that slot.

There are various failure conditions like temporary bans, auth expiration, and 
server downtime which the program can handle.


--- 

___This mini project concluded with a wonderful trip to Toronto and a successful renewal!___