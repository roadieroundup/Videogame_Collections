from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from sqlalchemy.orm import relationship

db = SQLAlchemy()


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))
    name = db.Column(db.String(1000))

    videogame_lists = relationship("VideogameList",
                                   back_populates="author", cascade="all, delete")


class VideogameList(db.Model):
    __tablename__ = "videogame_list"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    description = db.Column(db.String(250), nullable=False)
    img_url = db.Column(db.String(250), nullable=False)
    is_sorted = db.Column(db.Boolean, default=False)

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = relationship("User", back_populates="videogame_lists")

    videogames = relationship("Videogame", cascade="all, delete", backref="videogame_list")


class Videogame(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(250), nullable=False)
    rating = db.Column(db.Integer, nullable=True)

    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)

    list_id = db.Column(db.Integer, db.ForeignKey("videogame_list.id"))

    def __repr__(self):
        return f'id: {self.id}, title: {self.title}, year: {self.year}, description: {self.description}, rating: {self.rating}, review: {self.review}, img_url: {self.img_url}, list_id: {self.list_id}'
