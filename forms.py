from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField, IntegerField
from wtforms.validators import DataRequired, URL, NumberRange, Email
import email_validator


class RegisterForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired()])
    name = StringField("Name", validators=[DataRequired()])
    submit = SubmitField("Sign me up!")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Let me in!")


class NewListForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    description = StringField("Description", validators=[DataRequired()])
    img_url = StringField("List Image URL", validators=[DataRequired(), URL()])
    submit = SubmitField("Create List")


class AddForm(FlaskForm):
    title = StringField('Video game title', validators=[DataRequired()])
    submit = SubmitField('Search')


class EditGameForm(FlaskForm):
    rating = IntegerField('Your rating for this game (0 to 100)',
                          validators=[NumberRange(min=0, max=100, message='Please enter a number between 0 and 10')])
    review = StringField('Your Review', validators=[DataRequired()])
    submit = SubmitField('Done')
