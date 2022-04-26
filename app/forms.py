from flask_wtf import FlaskForm
from flask import url_for
from app import app
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
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
            if not (self.city.data or self.zipcode.data):
                self.city.errors.append('City or Zipcode must be provided.')
                self.zipcode.errors.append('City or Zipcode must be provided.')
                return False
            else:
                return True
        return False

    """with app.open_resource('static/performers.txt') as file:
        i = 0
        for line in file:
            line = line.decode("utf-8")
            my_choices.append(line.rstrip())
            i += 1
            if i > 30000:
                break
    """
    with app.open_resource('static/artists.json') as file:
        my_choices = json.load(file)
    my_choices = list(my_choices.keys())
    
    artists = SelectMultipleField('Enter artists:', validators=[DataRequired()], choices = my_choices)
    submit = SubmitField('Find Concerts')