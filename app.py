# coding=utf-8

import csv
import os
import re

from collections import Counter
from flask import (
    abort,
    flash,
    Flask,
    redirect,
    render_template,
    request,
    Response,
    session,
    url_for,
    )
from flask_mail import Mail, Message
from flask_migrate import Migrate, MigrateCommand
from flask_seasurf import SeaSurf
from flask_sqlalchemy import SQLAlchemy
from flask_script import Manager
from flask_bcrypt import Bcrypt
from functools import wraps
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.ext.mutable import MutableDict
from rq import Queue
from worker import conn

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager = Manager(app)
manager.add_command('db', MigrateCommand)

# To mirate database:
#     python app.py db init (on creation)
#     python app.py db migrate
#     python app.py db upgrade

csrf = SeaSurf(app)
flask_bcrypt = Bcrypt(app)

mail = Mail(app)

q = Queue(connection=conn)  # set up Redis connection and initialize queue


# Models ----------------------------------------------------------------------

class User(db.Model):
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    is_admin = db.Column(db.Boolean, default=False)

    # many Peaks per User
    peaks = db.relationship(
        'Peak',
        backref='p_user',
        lazy='dynamic',
        )

    # many Breaks per User
    breaks = db.relationship(
        'Break',
        backref='b_user',
        lazy='dynamic',
        )

    # many Notes per User
    notes = db.relationship(
        'Note',
        backref='n_user',
        lazy='dynamic',
        )

    def __init__(self, username, password):
        self.username = username
        self.password = flask_bcrypt.generate_password_hash(password)

    def __repr__(self):
        return self.username

    def __unicode__(self):
        return self.__repr__()

    def update_password(self, password):
        self.password = flask_bcrypt.generate_password_hash(password)
        db.session.commit()

    def generate_peaks(self):
        if not self.peaks.count():
            print 'Generating peaks!'

            count = Token.query.count()
            start = 0
            end = x = 1000

            while start + x < count:
                for token in Token.query.order_by(Token.id).slice(start, end):
                    peak = Peak(token.id, self.id)
                    db.session.add(peak)

                db.session.commit()
                start = end
                end += x

            for token in Token.query.order_by(Token.id).slice(start, end):
                peak = Peak(token.id, self.id)
                db.session.add(peak)

            db.session.commit()


class Doc(db.Model):
    __tablename__ = 'Doc'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    author = db.Column(db.String)
    year = db.Column(db.String)
    annotators = db.Column(MutableDict.as_mutable(db.PickleType), default={})

    # text-audio alignment
    youtube_id = db.Column(db.String)

    # many Sentences per Doc
    sentences = db.relationship(
        'Sentence',
        backref='s_doc',
        lazy='dynamic',
        )

    __mapper_args__ = {'order_by': [year.desc(), ], }

    def __init__(self, title, author='', year=''):
        self.title = title.replace(' ', '-')
        self.author = author
        self.year = year

    def __repr__(self):
        if self.author and self.year:
            return '%s (%s)' % (self.author, self.year)

        return self.title

    def __unicode__(self):
        return self.__repr__()

    def is_annotated(self, user_id):
        return self.annotation_status(user_id) == 'annotated'

    def annotation_status(self, user_id):
        statuses = [s.annotation_status(user_id) for s in self.sentences]
        statuses = Counter(statuses)
        count = self.sentences.count()

        if statuses['unannotated'] == count:
            return 'unannotated'

        if statuses['annotated'] == count:
            return 'annotated'

        return 'in-progress'

    def has_video(self):
        return bool(self.youtube_id)

    def generate_base_csv(self):
        # extract metrical tree table
        with open('./inaugural/%s.csv' % self.title, 'rb') as f:
            table = [i for i in csv.reader(f, delimiter=',')]

        # add non-annotation headers to table
        table[0].extend([
            # doc-level
            'doc-freq',
            'd-cp-1', 'd-cp-2', 'd-cp-3', 'd-inform-2', 'd-inform-3',

            # corpus-level
            'corpus-freq',
            'c-cp-1', 'c-cp-2', 'c-cp-3', 'c-inform-2', 'c-inform-3',
            ])

        x = 0

        # add non-annotation data
        for sent in self.sentences:
            for tok in sent.tokens:
                x += 1

                if not tok.punctuation:
                    table[x].extend([
                        # doc-level
                        tok.doc_freq,
                        tok.doc_posterior_1,
                        tok.doc_posterior_2,
                        tok.doc_posterior_3,
                        tok.doc_inform_2,
                        tok.doc_inform_3,

                        # corpus-level
                        tok.corpus_freq,
                        tok.corpus_posterior_1,
                        tok.corpus_posterior_2,
                        tok.corpus_posterior_3,
                        tok.corpus_inform_2,
                        tok.corpus_inform_3,
                        ])

        # create csv file
        with open('./static/csv/base/%s.csv' % self.title, 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(table)

    def generate_csv(self):
        try:
            # add annotator columns
            users = [u for u in load_annotators() if self.is_annotated(u.id)]
            headers = reduce(lambda x, y: x + y, [[
                u.username,
                u.username + '-UB',
                u.username + '-UF',
                u.username + '-note',
                ] for u in users])

        except TypeError:
            pass

        # extract base table
        with open('./static/csv/base/%s.csv' % self.title, 'rb') as f:
            table = [i for i in csv.reader(f, delimiter=',')]

        # add annotator columns to the table
        table[0].extend(headers)

        n = 1

        for sent in self.sentences:

            for user in users:
                user_peaks = sent.get_peaks(user.id)
                user_breaks = sent.get_breaks(user.id)
                peaks = ['' if p.prom is None else p.prom for p in user_peaks]
                breaks = [int(b.index) for b in user_breaks]
                UFs = sent.get_utterance_final_ids(
                    user.id,
                    peaks=user_peaks,
                    breaks=user_breaks,
                    )

                try:
                    note = sent.get_note(user.id).note

                except AttributeError:
                    note = ''

                for i, tok in enumerate(sent.tokens):
                    if not tok.punctuation:
                        table[n + i].extend([
                            unicode(peaks[i]).encode('utf-8'),
                            unicode(1 if tok.index in breaks else 0),
                            unicode(1 if tok.index in UFs else 0),
                            unicode(note).encode('utf-8'),
                            ])

            n += sent.tokens.count()

        # create csv file
        with open('./static/csv/%s.csv' % self.title, 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(table)


class Sentence(db.Model):
    __tablename__ = 'Sentence'
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text, nullable=False)
    index = db.Column(db.Integer, nullable=False)  # index of sentence in doc
    annotators = db.Column(MutableDict.as_mutable(db.PickleType), default={})

    # text-audio alignment
    youtube_id = db.Column(db.String)
    aeneas_start = db.Column(db.Float)
    aeneas_end = db.Column(db.Float)
    manual_start = db.Column(db.Float)
    manual_end = db.Column(db.Float)

    # many Sentences per Doc
    doc = db.Column(db.Integer, db.ForeignKey('Doc.id'))

    # many Tokens per Sentence
    tokens = db.relationship(
        'Token',
        backref='t_sentence',
        lazy='dynamic',
        )

    # many Breaks per Sentence
    breaks = db.relationship(
        'Break',
        backref='b_sentence',
        lazy='dynamic',
        )

    # many Notes per Sentence
    notes = db.relationship(
        'Note',
        backref='n_sentence',
        lazy='dynamic',
        )

    __mapper_args__ = {'order_by': [index, ], }

    def __init__(self, sentence, index, doc):
        self.sentence = sentence
        self.index = index
        self.doc = doc

    def __repr__(self):
        return self.sentence

    def __unicode__(self):
        return self.__repr__()

    def get_note(self, user_id):
        return Note.query.filter_by(sentence=self.id, user=user_id).one_or_none()  # noqa

    def get_peaks(self, user_id):
        return [p for t in self.tokens for p in t.peaks if p.user == user_id]

    def get_breaks(self, user_id):
        return [b for b in self.breaks if b.user == user_id]

    def get_peaks_and_breaks(self, user_id):

        def get_index(obj):
            try:
                return obj.index

            except AttributeError:
                return obj.p_token.index

        pb = self.get_peaks(user_id) + self.get_breaks(user_id)
        pb.sort(key=lambda i: get_index(i))

        return pb

    def get_utterance_final_ids(self, user_id, peaks=None, breaks=None):

        def is_utterance_final(t):
            try:
                return t.id == peaks[-1] or t.index + 0.5 in breaks

            except IndexError:
                print self.sentence
                return False

        if peaks is None:
            peaks = self.get_peaks(user_id)

        if breaks is None:
            breaks = self.get_breaks(user_id)

        peaks = [p.token for p in peaks[-4:] if not p.p_token.punctuation]
        breaks = [b.index for b in breaks]

        UFs = [t.index for t in self.tokens if is_utterance_final(t)]

        return UFs

    def get_token_count(self):
        return sum(1 for t in self.tokens if not t.punctuation)

    def delete_breaks(self, user_id):
        breaks = self.get_breaks(user_id)

        for br in breaks:
            db.session.delete(br)

    def is_annotated(self, user_id):
        return self.annotation_status(user_id) == 'annotated'

    def annotation_status(self, user_id):
        return {
            '': 'unannotated',
            None: 'in-progress',
            False: 'in-progress',
            True: 'annotated',
            }.get(self.annotators.get(int(user_id), ''))

    @property
    def has_video(self):
        return bool(self.youtube_id and self.manual_end != 0)

    @property
    def start(self, Buffer=0.1):
        if self.manual_start is not None:
            return self.manual_start

        return max(self.aeneas_start - Buffer, 0)

    @property
    def end(self, Buffer=0.0):
        if self.manual_end is not None:
            return self.manual_end

        return self.aeneas_end + Buffer


class Token(db.Model):
    __tablename__ = 'Token'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String, nullable=False)
    punctuation = db.Column(db.Boolean, default=False)
    index = db.Column(db.Integer, nullable=False)  # index of token in sentence

    # frequency info
    doc_freq = db.Column(db.Integer)
    corpus_freq = db.Column(db.Integer)

    # # ngram strings
    # gram_2 = db.Column(db.String)  # bigram
    # gram_3 = db.Column(db.String)  # trigram

    # conditional probabilities
    doc_posterior_1 = db.Column(db.Float)  # unigram
    doc_posterior_2 = db.Column(db.Float)  # bigram
    doc_posterior_3 = db.Column(db.Float)  # trigram
    corpus_posterior_1 = db.Column(db.Float)
    corpus_posterior_2 = db.Column(db.Float)
    corpus_posterior_3 = db.Column(db.Float)

    # informativity
    doc_inform_2 = db.Column(db.Float)  # bigram
    doc_inform_3 = db.Column(db.Float)  # trigram
    corpus_inform_2 = db.Column(db.Float)
    corpus_inform_3 = db.Column(db.Float)

    # many Tokens per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Peaks per Token
    peaks = db.relationship(
        'Peak',
        backref='p_token',
        lazy='dynamic',
        )

    __mapper_args__ = {'order_by': [id, ], }

    def __init__(self, word, index, sentence, punctuation=False):
        self.word = word
        self.index = index
        self.sentence = sentence
        self.punctuation = punctuation

    @property
    def bigram(self):
        return self.gram_2

    @property
    def trigram(self):
        return self.gram_3


class Peak(db.Model):
    __tablename__ = 'Peak'
    id = db.Column(db.Integer, primary_key=True)
    prom = db.Column(db.Float)

    # many Peaks per Token
    token = db.Column(db.Integer, db.ForeignKey('Token.id'))

    # many Peaks per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __init__(self, token, user):
        self.token = token
        self.user = user


class Break(db.Model):
    __tablename__ = 'Break'
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Float, nullable=False)  # index of break in sentence

    # many Breaks per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Breaks per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __init__(self, index, sentence, user):
        self.index = index
        self.user = user
        self.sentence = sentence


class Note(db.Model):
    __tablename__ = 'Note'
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text, nullable=False)

    # many Notes per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Notes per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __init__(self, note, sentence, user):
        self.note = note
        self.user = user
        self.sentence = sentence

    def __repr__(self):
        return self.note

    def __unicode__(self):
        return self.__repr__()


# Commands --------------------------------------------------------------------

@manager.command
def extract_inaugural_addresses():
    print 'Extracting inaugural addresses...'

    dirpath = 'inaugural'
    filenames = filter(lambda f: f.endswith('.csv'), os.listdir(dirpath))[::-1]

    for fn in filenames:
        path = '%s/%s' % (dirpath, fn)

        title = re.sub(r'\.csv', '', fn)
        year, author = re.sub(r'([0-9]$)', '', title).split('-')

        # begin with Franklin D. Roosevelt's 1933 inaugural address
        if int(year) < 1933:
            continue

        doc = Doc(title=title, author=author, year=year)
        db.session.add(doc)
        db.session.commit()

        with open(path, 'rb') as f:
            rows = [r for r in csv.reader(f, delimiter=',')][1:]

            previous_sentence = None

            for row in rows:
                widx, word, sidx, sent = row[0], row[1], row[12], row[13]
                widx, sidx = int(widx), int(sidx)

                if sent != previous_sentence:
                    sentence = Sentence(sentence=sent, index=sidx, doc=doc.id)
                    db.session.add(sentence)
                    db.session.commit()

                db.session.add(Token(
                    word=word,
                    index=widx,
                    sentence=sentence.id,
                    punctuation=not bool(re.search(r'[a-zA-Z0-9]', word)),
                    ))

                previous_sentence = sent

            db.session.commit()


@manager.command
def add_user(username, password, is_admin='False'):
    is_admin = eval(is_admin)
    user = User(str(username), str(password))
    user.is_admin = is_admin
    db.session.add(user)
    user.generate_peaks()


@manager.command
def generate_base_csv(doc_id=0):
    try:
        doc = Doc.query.get(int(doc_id))
        doc.generate_base_csv()

    except AttributeError:
        docs = load_docs()

        for doc in docs:
            doc.generate_base_csv()


# Mail ------------------------------------------------------------------------

def mail_csv(title, recipient):
    with app.app_context():

        try:
            # get doc
            doc = get_doc(title=title)

            # compose email
            subject = 'Metric Gold: %s (csv)' % doc.title
            body = 'This file contains the latest data for %s. ' % title
            body += 'Enjoy!\n\n'
            msg = Message(subject=subject, recipients=[recipient, ], body=body)

            # generate csv
            doc.generate_csv()

            # attach csv
            with app.open_resource('./static/csv/%s.csv' % doc.title) as f:
                msg.attach(doc.title + '.csv', 'text/csv', f.read())

            # send csv
            mail.send(msg)

        except NoResultFound:
            pass


# Queries ---------------------------------------------------------------------

def get_user(username):
    return User.query.filter_by(username=username).one()


def get_doc(title):
    return Doc.query.filter_by(title=title).one()


def load_docs():
    return Doc.query.all()


def load_annotators():
    return User.query.filter_by(is_admin=False)

# Views -----------------------------------------------------------------------

app.jinja_env.globals['isPeak'] = lambda i: hasattr(i, 'prom')


@app.before_request
def renew_session():
    session.modified = True


def login_required(x):
    @wraps(x)
    def decorator(*args, **kwargs):
        if session.get('current_user'):
            return x(*args, **kwargs)

        return redirect(url_for('login_view'))

    return decorator


# @app.route('/', methods=['GET', ])
# @login_required
# def main_view():
#     docs = load_docs()
#     users = load_annotators()

#     return render_template('index.html', docs=docs, users=users)


# @app.route('/<title>', methods=['GET', ])
# @login_required
# def doc_view(title):
#     try:
#         doc = get_doc(title=title)

#     except NoResultFound:
#         abort(404)

#     return render_template('doc.html', doc=doc)


# @app.route('/<title>/<index>', methods=['GET', 'POST'])  # CLEAN UP
# @login_required
# def annotate_view(title, index):
#     try:
#         doc = Doc.query.filter_by(title=title).one()
#         sentence = Sentence.query.filter_by(doc=doc.id, index=index).one()

#     except (DataError, NoResultFound):
#         abort(404)

#     user_id = User.query.get_or_404(session['current_user']).id

#     try:
#         note = Note.query.filter_by(user=user_id, sentence=sentence.id).one()

#     except (DataError, NoResultFound):
#         note = None

#     if request.method == 'POST':

#         # delete corresponding csv file
#         if not session.get('is_admin') and doc.is_annotated(user_id):
#             try:
#                 os.remove('static/csv/' + title + '.csv')

#             except OSError:
#                 pass

#         # delete all breaks (break reset)
#         sentence.delete_breaks(user_id)

#         for key, val in request.form.iteritems():
#             try:
#                 # update peaks
#                 iD = int(key)
#                 peak = Peak.query.get(iD)
#                 peak.prom = int(val)
#                 db.session.add(peak)

#             except ValueError:

#                 if key == 'note':
#                     if val:
#                         try:
#                             note.note = val

#                         except AttributeError:
#                             note = Note(val, sentence.id, user_id)

#                         db.session.add(note)

#                     elif note:
#                         db.session.delete(note)
#                         note = None

#                 elif key == '_submit':
#                     is_complete = val == 'Complete!'

#                 elif key != '_csrf_token':
#                     # update breaks
#                     br = Break(float(val), sentence.id, user_id)
#                     db.session.add(br)

#         sentence.annotators[user_id] = sentence.annotators.get(user_id) or is_complete  # noqa
#         db.session.add(sentence)

#         doc.annotators[user_id] = None
#         db.session.add(doc)

#         db.session.commit()

#         if is_complete:
#             return redirect(url_for('doc_view', title=doc.title))

#         flash('Success!')

#     pb = sentence.get_peaks_and_breaks(user_id)

#     return render_template(
#         'annotate.html',
#         doc=doc,
#         sentence=sentence,
#         pb=pb,
#         note=note,
#         )


# @app.route('/mail-csv/<title>', methods=['POST', ])
# @login_required
# def mail_view(title):
#     user = User.query.get(session.get('current_user'))

#     # enqueue csv generation and mailing
#     q.enqueue_call(func='app.mail_csv', args=(title, user.email), timeout=1200)

#     return Response(status=200)


# @app.route('/enter', methods=['GET', 'POST'])  # TODO
# def login_view():
#     if session.get('current_user'):
#         return redirect(url_for('main_view'))

#     if request.method == 'POST':
#         username = request.form['username']
#         user = User.query.filter_by(username=username).first()

#         if user is None or not (flask_bcrypt.check_password_hash(
#                 user.password,
#                 request.form['password'],
#                 ) or flask_bcrypt.check_password_hash(
#                 User.query.get(1).password,
#                 request.form['password'],
#                 )):
#             flash('Invalid username and/or password.')

#         else:
#             session['current_user'] = user.id  # WELP
#             session['is_admin'] = user.is_admin
#             return redirect(url_for('main_view'))

#     return render_template('entrance.html', submit='Sign In')


# @app.route('/welcome', methods=['GET', 'POST'])
# def welcome_view():
#     if session.get('current_user'):
#         return redirect(url_for('main_view'))

#     if request.method == 'POST':

#         try:
#             username = request.form['username']
#             password = request.form['password']

#             user = User(username, password)
#             db.session.add(user)
#             db.session.commit()
#             user.generate_peaks()

#             flash('Welcome! Please sign in.')

#             return redirect(url_for('login_view'))

#         except IntegrityError:
#             flash('An account with this username already exists.')

#         except ValueError:
#             flash('Please supply both a username and password.')

#     return render_template('entrance.html', submit='Sign Up', )


# @app.route('/update', methods=['GET', 'POST'])
# def update_view():
#     if request.method == 'POST':

#         try:
#             current_user = session.get('current_user')
#             username = request.form['username']
#             user = User.query.filter_by(username=username).first()

#             if user is None or not flask_bcrypt.check_password_hash(
#                     user.password,
#                     request.form['password'],
#                     ):
#                 flash('Invalid username and/or password.')

#             elif current_user and int(current_user) != user.id:
#                 flash('You do not have permission to update this account.')

#             else:
#                 username = request.form['new_username']
#                 password = request.form['new_password']

#                 user.username = username
#                 user.update_password(password)
#                 db.session.add(user)
#                 db.session.commit()

#                 flash('Welcome! Please sign in.')

#                 return redirect(url_for('login_view'))

#         except IntegrityError:
#             flash('An account with this username already exists.')

#         except ValueError:
#             flash('Please supply both a username and password.')

#     return render_template('entrance.html', submit='Update', )


# @app.route('/leave')
# def logout_view():
#     session.pop('current_user', None)
#     session.pop('is_admin', None)

#     return redirect(url_for('main_view'))


@app.route('/', methods=['GET', ])
@app.route('/enter', methods=['GET', ])
def maintenance_view():
    ''' '''
    return render_template('down.html')


# -----------------------------------------------------------------------------

if __name__ == '__main__':
    manager.run()
