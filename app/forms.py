from flask_wtf import FlaskForm
from flask import url_for
from app import app
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectMultipleField, DateField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from app.models import User
import json

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min = 2, max = 20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min = 2, max = 20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class ConcertForm(FlaskForm):
    city = StringField('Enter city:', validators=[Length(max = 90)])
    zipcode = StringField('Enter zip code:', validators=[Length(max = 9)])

    def validate(self, extra_validators=None):
        if super().validate(extra_validators):
            if self.city.data and self.zipcode.data:
                error_msg = 'Search using city or zip code, but not both.'
                self.city.errors.append(error_msg)
                self.zipcode.errors.append(error_msg)
                return False
            if not (self.artists.data or self.search_saved_artists.data or self.city.data or self.zipcode.data):
                error_msg = 'Search must include city, zipcode, or artists.'
                self.city.errors.append(error_msg)
                self.zipcode.errors.append(error_msg)
                self.artists.errors.append(error_msg)
            else:
                return True
        return False

    with app.open_resource('static/artists.json') as file:
        my_choices = json.load(file)
    my_choices = list(my_choices.keys())

    artists = SelectMultipleField('Enter artists:', choices = my_choices, validate_choice=False)
    search_saved_artists = BooleanField('Search using saved artists')
    save_artists = BooleanField('Add artists from search field to saved artists')
    save_city = BooleanField('Save city for future searches', default='checked')
    start_date = DateField('Enter start date:', validators=[Optional()])
    end_date = DateField('Enter end date:', validators=[Optional()])
    submit = SubmitField('Find Concerts')

class RequestResetForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Request Password Reset')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is None:
            raise ValidationError('There is no account with that email. You must register first.')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')
    