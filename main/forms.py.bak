from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, validators, SelectField, DateField, DecimalField
from wtforms.validators import DataRequired
from wtforms import Form
from wtforms_components import DateTimeField, DateRange, IntegerField, TimeField, TimeRange
from datetime import date,timedelta
import datetime
from datetime import datetime
from main.models import Staff


from flask import current_app
#from flask import g

class EditEventForm(FlaskForm):
    edit_event_id= IntegerField("id",validators=[validators.Optional()])
    event_title = StringField("event_title", [validators.required()])
    course_name =StringField("course_name", [validators.required()])#db.Column(db.String(255),nulllible=False)
    event_description = StringField("event_description")
    submit_button = SubmitField("Create Event")


class AssignStaff(FlaskForm):
    add_staff = SelectField("Select Staff Member")
    add_wrk=DecimalField('Set Workload')


class DelTeamsForm(FlaskForm):
    edit_teams_id = IntegerField('Event id', [validators.required(), validators.Length(min=10, max=10, message="event id")])  # StringField("Title", [validators.required(), validators.length(max=255)])
    submit_button = SubmitField("Delete Block")

    def validate(self):
        if self.date.data is None:
            return False
        else:
            return True