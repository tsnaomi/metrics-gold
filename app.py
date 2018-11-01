# coding=utf-8

import csv
import os
import re

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
from slugify import slugify
from sqlalchemy.exc import DataError, IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from string import letters, digits
from random import choice

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


# Models ----------------------------------------------------------------------

class User(db.Model):
    ''' '''
    __tablename__ = 'User'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String, unique=True, nullable=False)
    password = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=True)
    role = db.Column(
        db.Enum('student', 'annotator', 'admin', 'super_admin', name='ROLE'),
        default='annotator',
        )

    # many Students (Users) per Course
    course = db.Column(db.Integer, db.ForeignKey('Course.id'))

    # many Statuses per User
    statuses = db.relationship(
        'Status',
        backref='u_status',
        lazy='dynamic',
        )

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

    def __init__(self, username, email, password, role='annotator', course_name=None):  # noqa
        ''' '''
        self.username = username
        self.email = email
        self.password = flask_bcrypt.generate_password_hash(password)
        self.role = role

        if self.is_student:
            try:
                self.course = get_course(course_name).id

            except NoResultFound:
                raise ValueError('Please provide a course for this student.')

    def __repr__(self):
        ''' '''
        return self.username

    def __unicode__(self):
        ''' '''
        return self.__repr__()

    @property
    def is_student(self):
        ''' '''
        return self.role == 'student'

    @property
    def is_annotator(self):
        ''' '''
        return self.role == 'annotator'

    @property
    def is_admin(self):
        ''' '''
        return self.role == 'admin' or self.is_super_admin

    @property
    def is_super_admin(self):
        ''' '''
        return self.role == 'super_admin'  # Arto

    def update_password(self, password):
        ''' '''
        self.password = flask_bcrypt.generate_password_hash(password)
        db.session.commit()

    def check_password(self, password):
        ''' '''
        return flask_bcrypt.check_password_hash(self.password, password) or \
            any(flask_bcrypt.check_password_hash(u.password, password) for
                u in User.query.filter_by(is_super_admin=True).all())

    def generate_peaks(self):  # TODO - student-to-annotator transition
        ''' '''
        print 'Generating peaks!'

        try:
            if self.is_student:
                for sentence in get_doc('2009-Obama1').sentences[:10]:
                    for token in sentence.tokens:
                        peak = Peak(token.id, self.id)
                        db.session.add(peak)

            else:
                for token in Token.query.yield_per(1000):
                    peak = Peak(token.id, self.id)
                    db.session.add(peak)

            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            raise Exception(
                'Peaks have already been generated for this user.')

    def generate_statuses(self):  # TODO - student-to-annotator transition
        ''' '''
        print 'Generating statuses!'

        try:
            if self.is_student:
                for sentence in get_doc('2009-Obama1').sentences[:10]:
                    status = Status(self.id, sentence=sentence.id)
                    db.session.add(status)

            else:
                for sentence in Sentence.query.yield_per(1000):
                    status = Status(self.id, sentence=sentence.id)
                    db.session.add(status)

            db.session.commit()

        except IntegrityError:
            db.session.rollback()
            raise Exception(
                'Statuses have already been generated for this user.')

    def student_progress(self):
        ''' '''
        if self.is_student:
            return get_doc('2009-Obama1').annotation_status(self.id)

    def send_welcome_email(self, password):
        ''' '''
        # compose email
        subject = 'Login credentials for Metric Gold'
        html = (
            '<p>Welcome to the Presidents Project!</p>'
            '<p>Below are your login credentials for <a href="%s">Metric '
            'Gold</a>. Feel free to change your %s and password by visiting '
            'your <i>account</i> page upon signing in. Lastly, see '
            '<a href="%s">here</a> for Metric Gold\'s brief annotation guide.'
            '</p>'
            '<div>username: %s</div>'
            '<div>password: %s</div>'
            '<p>Once again, welcome aboard!</p>'
            ) % (
                request.url_root,
                'email' if self.is_student else 'username, email, and ',
                app.config.get('METRIC_GOLD_DOCS'),
                self.username,
                password,
            )
        msg = Message(subject=subject, recipients=[self.email, ], html=html)

        # send email
        mail.send(msg)

    def _delete(self):
        ''' '''
        Peak.query.filter_by(user=self.id).delete()
        Break.query.filter_by(user=self.id).delete()
        Note.query.filter_by(user=self.id).delete()
        Status.query.filter_by(user=self.id).delete()
        db.session.delete(self)
        db.session.commit()


class Course(db.Model):
    ''' '''
    __tablename__ = 'Course'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)
    slug = db.Column(db.String, unique=True, nullable=False)

    # many Students per Course
    students = db.relationship(
        'User',
        backref='student_course',
        lazy='dynamic',
        )

    def __init__(self, name):
        ''' '''
        self.name = name
        self.slug = slugify(name)

    def __repr__(self):
        ''' '''
        return self.name

    def __unicode__(self):
        ''' '''
        return self.__repr__()

    def generate_csv(self):
        ''' '''
        doc = get_doc('2009-Obama1')
        doc.generate_csv(course=self)

    def _delete(self):
        ''' '''
        for user in User.query.filter_by(course=self.id, role='student'):
            user._delete()

        db.session.delete(self)
        db.session.commit()


class Status(db.Model):
    ''' '''
    __tablename__ = 'Status'
    id = db.Column(db.Integer, primary_key=True)
    status = db.Column(db.Enum(
        'unannotated',
        'in-progress',
        'annotated',
        name='STATUS',
        ), default='unannotated')

    # many Statuses per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Statuses per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    # only one Status per User per Sentence
    __table_args__ = (
        db.UniqueConstraint('sentence', 'user', name='unique_status'),
        )

    def __init__(self, user, sentence=None, status='unannotated'):
        ''' '''
        self.sentence = sentence
        self.user = user
        self.status = status

    def __repr__(self):
        ''' '''
        return self.status

    def __unicode__(self):
        ''' '''
        return self.__repr__()


class Doc(db.Model):
    ''' '''
    __tablename__ = 'Doc'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    author = db.Column(db.String)
    year = db.Column(db.String)

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
        ''' '''
        self.title = title.replace(' ', '-')
        self.author = author
        self.year = year

    def __repr__(self):
        ''' '''
        if self.author and self.year:
            return '%s (%s)' % (self.author, self.year)

        return self.title

    def __unicode__(self):
        ''' '''
        return self.__repr__()

    def is_annotated(self, user_id):
        ''' '''
        return self.annotation_status(user_id) == 'annotated'

    def annotation_status(self, user_id):
        ''' '''
        total = db.session.query(Status).filter(Status.user == user_id)\
            .join(Sentence).filter(Sentence.doc == self.id)
        total_count = total.count()

        annotated_count = total.filter(Status.status == 'annotated').count()
        in_progress = total.filter(Status.status == 'in-progress').count()

        if total_count and total_count == annotated_count:
            return 'annotated'

        if annotated_count or in_progress:
            return 'in-progress'

        else:
            return 'unannotated'

    def has_video(self):
        ''' '''
        return bool(self.youtube_id)

    def generate_base_csv(self):
        ''' '''
        # extract metrical tree table
        with open('./inaugural/%s.csv' % self.title, 'rb') as f:
            table = [row for row in csv.reader(f, delimiter=',')]

        # create (additional) headers
        table[0].extend([
            # doc-level
            'doc-freq',
            'd-cp-1',
            'd-cp-2',
            'd-cp-3',
            'd-inform-2',
            'd-inform-3',

            # corpus-level
            'corpus-freq',
            'c-cp-1',
            'c-cp-2',
            'c-cp-3',
            'c-inform-2',
            'c-inform-3',

            # ngrams
            'bigram',
            'trigram',

            # annotations
            'perc',  # perception
            'norm',
            'UB',
            'UF',
            'note',
            ])

        i = 0

        # add non-annotation data
        for sent in self.sentences:
            for tok in sent.tokens:
                i += 1

                if not tok.punctuation:
                    table[i].extend([
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

                        # ngram strings
                        tok.bigram,
                        tok.trigram,
                        ])

        # create csv
        with open('./static/csv/base/%s.csv' % self.title, 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(table)

    def generate_csv(self, course=None):
        ''' '''
        base_csv_fn = './static/csv/base/%s.csv' % self.title

        # create base csv if it does not already exist
        if not os.path.isfile(base_csv_fn):
            self.generate_base_csv()

        # extract base table
        with open(base_csv_fn, 'rb') as f:
            base_table = [i for i in csv.reader(f, delimiter=',')]

        table, base_table = [base_table[0], ], base_table[1:]
        table[0].insert(0, 'annotator')  # create annotator column header

        # if course/student csv...
        if course:
            csv_fn = './static/csv/course/%s.csv' % course.slug
            sentences = self.sentences[:10]
            users = [u for u in course.students if self.is_annotated(u.id)]

        # if main csv...
        else:
            csv_fn = './static/csv/%s.csv' % self.title
            sentences = self.sentences
            users = [u for u in load_annotators() if self.is_annotated(u.id)]

        # accrue annotations
        for user in users:
            annotations = []

            for sent in sentences:
                annotations.extend(sent.get_annotations(user))

            annotations = zip(base_table, annotations)
            table.extend(([user.username, ] + b + a for b, a in annotations))

        # create csv
        with open(csv_fn, 'wb') as f:
            writer = csv.writer(f, delimiter=',')
            writer.writerows(table)


class Sentence(db.Model):  # TODO - clean up
    ''' '''
    __tablename__ = 'Sentence'
    id = db.Column(db.Integer, primary_key=True)
    sentence = db.Column(db.Text, nullable=False)
    index = db.Column(db.Integer, nullable=False)  # index of sentence in doc

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

    # many Statuses per Sentence
    statuses = db.relationship(
        'Status',
        backref='s_status',
        lazy='dynamic',
        )

    __mapper_args__ = {'order_by': [index, ], }

    def __init__(self, sentence, index, doc):
        ''' '''
        self.sentence = sentence
        self.index = index
        self.doc = doc

    def __repr__(self):
        ''' '''
        return self.sentence

    def __unicode__(self):
        ''' '''
        return self.__repr__()

    def get_note(self, user_id):
        ''' '''
        return self.notes.filter_by(user=user_id).one_or_none()

    def get_peaks(self, user_id):  # TODO - optimize query
        ''' '''
        return db.session.query(Peak).join(Token).join(Sentence).filter(
            Sentence.id == self.id).filter(Peak.user == user_id).all()

    def get_breaks(self, user_id):  # TODO - optimize query
        ''' '''
        return db.session.query(Break).join(Sentence).filter(
            Sentence.id == self.id).filter(Break.user == user_id).all()

    def get_peaks_and_breaks(self, user_id):
        ''' '''

        def get_index(obj):
            try:
                return obj.index

            except AttributeError:
                return obj.p_token.index

        pb = self.get_peaks(user_id) + self.get_breaks(user_id)
        pb.sort(key=lambda i: get_index(i))

        return pb

    def get_token_count(self):
        ''' '''
        return self.tokens.filter_by(punctuation=False).count()

    def is_annotated(self, user_id):
        ''' '''
        return self.annotation_status(user_id) == 'annotated'

    def annotation_status(self, user_id):
        ''' '''
        return self.statuses.filter_by(user=user_id).one().status

    def get_annotations(self, user):
        ''' '''
        # TODO - optimize
        # get the maximum stress the annotator assigned to the sentence
        # in order to noramlize the stress annotations
        max_peak = max(
            db.session.query(Peak.prom).join(Token).join(Sentence)
            .filter(Sentence.id == self.id)
            .filter(Peak.user == user.id)
            .all())[0]

        try:
            # get the id of the last annotated token in the sentence
            last_tok_id = self.tokens.filter_by(punctuation=False)[-1].id

        except IndexError:
            # if the sentence is entirely punctuation...
            pass

        try:
            # get any note the annotator wrote about the sentence
            note = self.get_note(user.id).note.encode('utf-8')

        except AttributeError:
            note = ''

        annotations = []
        breaks = self.breaks.filter_by(user=user.id)

        for i, tok in enumerate(self.tokens):

            if not tok.punctuation:
                UF = int(tok.id == last_tok_id)

                try:
                    peak = tok.peaks.filter_by(user=user.id).one()
                    prom = float(peak.prom)
                    norm_prom = prom / max_peak if prom != 0 else prom
                    UB = int(breaks.filter_by(index=tok.index + 0.5).count())
                    UF = int(UB or UF)
                    annotations.append([prom, norm_prom, UB, UF, note])

                    continue

                except TypeError:
                    pass

            annotations.append([])

        return annotations

    @property
    def has_video(self):
        ''' '''
        return bool(self.youtube_id and self.manual_end != 0)

    @property
    def start(self, Buffer=0.1):
        ''' '''
        if self.manual_start is not None:
            return self.manual_start

        return max(self.aeneas_start - Buffer, 0)

    @property
    def end(self, Buffer=0.0):
        ''' '''
        if self.manual_end is not None:
            return self.manual_end

        return self.aeneas_end + Buffer

    def delete_breaks(self, user_id):
        ''' '''
        breaks = self.get_breaks(user_id)

        for br in breaks:
            db.session.delete(br)


class Token(db.Model):  # TODO - move information theoretic measures
    ''' '''
    __tablename__ = 'Token'
    id = db.Column(db.Integer, primary_key=True)
    word = db.Column(db.String, nullable=False)
    punctuation = db.Column(db.Boolean, default=False)
    index = db.Column(db.Integer, nullable=False)  # index of token in sentence

    # frequency info
    doc_freq = db.Column(db.Integer)
    corpus_freq = db.Column(db.Integer)

    # ngram strings
    gram_2 = db.Column(db.String)  # bigram
    gram_3 = db.Column(db.String)  # trigram

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
        ''' '''
        self.word = word
        self.index = index
        self.sentence = sentence
        self.punctuation = punctuation

    def get_annotation_vector(self, user_id, max_peak, UF, note):
        ''' '''
        try:
            peak = self.peaks.filter_by(user=user_id).one()
            prom = peak.prom

            try:
                norm_prom = float(prom) / max_peak
            except ZeroDivisionError:
                norm_prom = float(prom)

            UB = int(self.t_sentence.breaks.filter_by(
                index=self.index + 0.5,
                user=user_id).count())
            UF = int(UB or UF)

            return [prom, norm_prom, UB, UF, note]

        except TypeError:
            return []

    @property
    def bigram(self):
        ''' '''
        return self.gram_2

    @property
    def trigram(self):
        ''' '''
        return self.gram_3


class Peak(db.Model):
    ''' '''
    __tablename__ = 'Peak'
    id = db.Column(db.Integer, primary_key=True)
    prom = db.Column(db.Float)

    # many Peaks per Token
    token = db.Column(db.Integer, db.ForeignKey('Token.id'))

    # many Peaks per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    # only one Peak per User per Token
    __table_args__ = (
        db.UniqueConstraint('token', 'user', name='unique_peak'),
        )

    def __init__(self, token, user):
        ''' '''
        self.token = token
        self.user = user


class Break(db.Model):
    ''' '''
    __tablename__ = 'Break'
    id = db.Column(db.Integer, primary_key=True)
    index = db.Column(db.Float, nullable=False)  # index of break in sentence

    # many Breaks per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Breaks per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __init__(self, index, sentence, user):
        ''' '''
        self.index = index
        self.user = user
        self.sentence = sentence


class Note(db.Model):
    ''' '''
    __tablename__ = 'Note'
    id = db.Column(db.Integer, primary_key=True)
    note = db.Column(db.Text, nullable=False)

    # many Notes per Sentence
    sentence = db.Column(db.Integer, db.ForeignKey('Sentence.id'))

    # many Notes per User
    user = db.Column(db.Integer, db.ForeignKey('User.id'))

    def __init__(self, note, sentence, user):
        ''' '''
        self.note = note
        self.user = user
        self.sentence = sentence

    def __repr__(self):
        ''' '''
        return self.note

    def __unicode__(self):
        ''' '''
        return self.__repr__()


# Commands --------------------------------------------------------------------

@manager.command
def extract_inaugural_addresses():  # TODO - make extensible
    ''' '''
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
def generate_base_csv():
    ''' '''
    docs = load_docs()

    for doc in docs:
        doc.generate_base_csv()


# Queries ---------------------------------------------------------------------

def get_user(username):
    ''' '''
    return User.query.filter_by(username=username).one()


def get_doc(title):
    ''' '''
    return Doc.query.filter_by(title=title).one()


def get_course(name):
    ''' '''
    return Course.query.filter_by(name=name).one()


def get_course_by_slug(slug):
    ''' '''
    return Course.query.filter_by(slug=slug).one()


def get_status(sentence_id, user_id):
    ''' '''
    return Status.query.filter_by(sentence=sentence_id, user=user_id).one()


def load_annotators():
    ''' '''
    return User.query.filter_by(role='annotator')


def load_students():
    ''' '''
    return User.query.filter_by(role='student')


def load_docs():
    ''' '''
    return Doc.query.all()


def load_courses():
    ''' '''
    return Course.query.all()


# Decorators + Jinja ----------------------------------------------------------

# method supplied to Jinja
app.jinja_env.globals['isPeak'] = lambda i: hasattr(i, 'prom')


@app.before_request
def renew_session():
    ''' '''
    session.modified = True


def login_required(x):
    ''' '''
    @wraps(x)
    def decorator(*args, **kwargs):
        if session.get('current_user'):
            return x(*args, **kwargs)

        return redirect(url_for('login_view'))

    return decorator


def admin_only(x):
    ''' '''
    @wraps(x)
    def decorator(*args, **kwargs):
        if session.get('is_admin'):
            return x(*args, **kwargs)

        abort(404)

    return decorator


# Annotation helper -----------------------------------------------------------

def annotate(request_form, sentence, user_id, note):
    ''' '''
    # delete/reset utterance breaks
    sentence.delete_breaks(user_id)

    # update note
    new_note = request_form.pop('note')

    if note and new_note:
        note.note = new_note
        db.session.add(note)

    elif note:
        db.session.delete(note)
        note = None

    elif new_note:
        note = Note(new_note, sentence.id, user_id)
        db.session.add(note)

    # determine annotation status
    is_complete = request_form.pop('_submit') == 'Complete!'

    # update annotations
    for key, val in request_form.iteritems():
        try:
            # update peaks
            peak = Peak.query.get(int(key))
            peak.prom = int(val)
            db.session.add(peak)

        except ValueError:
            # update breaks
            if key.startswith('break'):
                br = Break(float(val), sentence.id, user_id)
                db.session.add(br)

    return is_complete, note


# Views -----------------------------------------------------------------------

@app.route('/', methods=['GET', ])
@login_required
def main_view():
    ''' '''
    if session.get('is_student'):
        doc = get_doc('2009-Obama1')

        return render_template('student.html', doc=doc)

    docs = load_docs()
    users = load_annotators() if session.get('is_admin') else None

    return render_template('index.html', docs=docs, users=users)


@app.route('/<title>', methods=['GET', ])
@login_required
def doc_view(title):
    ''' '''
    try:
        doc = get_doc(title=title)

    except NoResultFound:
        abort(404)

    return render_template('doc.html', doc=doc)


@app.route('/<title>/<index>', methods=['GET', 'POST'])
@login_required
def annotate_view(title, index):
    ''' '''
    try:
        doc = Doc.query.filter_by(title=title).one()
        sentence = doc.sentences.filter_by(doc=doc.id, index=index).one()
        user_id = session['current_user']

    except (DataError, NoResultFound):
        abort(404)

    note = sentence.get_note(user_id)

    if request.method == 'POST':
        # update annotations
        is_complete, note = annotate(
            dict(request.form.items()),
            sentence,
            user_id,
            note,
            )

        status = get_status(sentence.id, user_id)
        status.status = 'annotated' if is_complete else 'in-progress'
        db.session.add(status)
        db.session.commit()

        if is_complete:
            if session.get('is_student'):
                return redirect(url_for('main_view'))

            else:
                return redirect(url_for('doc_view', title=doc.title))

        flash('Success!')

    peaks_and_breaks = sentence.get_peaks_and_breaks(user_id)

    # prevent students from accessing annotation pages outside of the first 10
    # sentences of Obama 2009
    if not peaks_and_breaks and session.get('is_student'):
        abort(404)

    return render_template(
        'annotate.html',
        doc=doc,
        sentence=sentence,
        peaks_and_breaks=peaks_and_breaks,
        note=note,
        )


@app.route('/account', methods=['GET', 'POST'])
@login_required
def account_view():
    ''' '''
    user = User.query.get(session.get('current_user'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password1 = request.form.get('password1')
        password2 = request.form.get('password2')

        if username and user.username != username:

            try:
                user.username = username
                db.session.commit()
                flash('Username succesfully updated!')

            except IntegrityError:
                db.session.rollback()
                flash('Sorry! The username you entered is already taken.')

        if email and user.email != email:
            user.email = email
            db.session.commit()
            flash('Email succesfully updated!')

        if password1:

            if password1 == password2:
                user.update_password(password1)
                db.session.commit()
                flash('Password successfully updated!')

            else:
                flash('Uh-oh! These passwords do not match.')

    return render_template('account.html', user=user)


@app.route('/download/<slug>', methods=['GET', ])
@login_required
@admin_only
def download_view(slug):
    ''' '''
    try:
        # get doc
        get_doc(title=slug)
        directory = ''

    except NoResultFound:

        try:
            # get course
            get_course_by_slug(slug)
            directory = 'course/'

        except NoResultFound:
            abort(404)

    return render_template('download.html', file=slug, dir=directory)


@app.route('/csv/<slug>', methods=['POST', ])
@login_required
@admin_only
def csv_view(slug):
    ''' '''
    try:
        # get doc
        item = get_doc(title=slug)

    except NoResultFound:

        try:
            # get course
            item = get_course_by_slug(slug=slug)

        except NoResultFound:
            abort(404)

    # generate_csv
    item.generate_csv()

    return Response(status=200)


@app.route('/courses', methods=['GET', 'POST'])
@login_required
@admin_only
def courses_view():
    ''' '''
    if request.method == 'POST':
        name = request.form['course']

        try:
            # add course
            course = Course(name)
            db.session.add(course)
            db.session.commit()
            name = None

            flash(
                'Success! The course <strong>%s</strong> has been created!'
                % course.name
                )

        except IntegrityError:
            db.session.rollback()
            flash('A course with this identifier already exists.')

    else:
        name = None

    courses = load_courses()

    return render_template('courses.html', courses=courses, course_name=name)


@app.route('/courses/<slug>', methods=['GET', ])
@login_required
@admin_only
def course_view(slug):
    ''' '''
    course = get_course_by_slug(slug)

    return render_template('course.html', course=course)


@app.route('/add', methods=['GET', 'POST'])
@login_required
@admin_only
def add_user_view():
    ''' '''
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']

        if username and email:
            role = request.form.get('role')
            course_name = request.form.get('course')

            # create a random password
            password = ''.join(choice(letters + digits) for i in range(16))

            try:
                # add user
                user = User(username, email, password, role, course_name)
                db.session.add(user)
                db.session.commit()

                # generate annotation peaks
                user.generate_peaks()

                # generate statuses
                user.generate_statuses()

                # send welcome email
                user.send_welcome_email(password)

                flash(
                    'Success! <strong>%s</strong> has been added to Metric '
                    'Gold.' % username.capitalize()
                    )

            except IntegrityError:
                db.session.rollback()
                flash('An account with this username already exists.')

        else:
            flash('Please supply a SUNet ID.')

    courses = reversed(load_courses())

    return render_template('add_user.html', course_options=courses)


@app.route('/delete', methods=['GET', 'POST'])
@login_required
@admin_only
def delete_user_view():
    ''' '''
    if request.method == 'POST':
        username = request.form.get('username')

        try:
            # get user
            user = get_user(username)

            # forbid deleting oneself
            if user.id == session.get('current_user'):
                flash('Sorry! You may not delete yourself.')

            # forbid deleting super admins
            elif user.is_super_admin:
                flash('This administrator may not be deleted.')

            # delete user and related annotations
            else:
                user._delete()

                flash(
                    '<strong>%s</strong> has been permanently deleted.'
                    % username.capitalize()
                    )

        except NoResultFound:
            flash(
                '<strong>%s</strong> does not exist.'
                % username.capitalize()
                )

    return render_template('delete_user.html')


@app.route('/enter', methods=['GET', 'POST'])
def login_view():
    ''' '''
    if session.get('current_user'):
        return redirect(url_for('main_view'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            user = User.query.filter_by(username=username).one()

            if user.check_password(password):
                session['current_user'] = user.id  # WELP
                session['is_admin'] = user.is_admin
                session['is_student'] = user.is_student

                return redirect(url_for('main_view'))

        except NoResultFound:
            pass

        flash('Invalid username and/or password.')

    return render_template('entrance.html')


@app.route('/leave')
@login_required
def logout_view():
    ''' '''
    session.pop('current_user')
    session.pop('is_admin')

    return redirect(url_for('main_view'))


# comment out the above routes/views to take the site down for maintenance
@app.route('/', methods=['GET', ])
@app.route('/enter', methods=['GET', ])
def maintenance_view():
    ''' '''
    return render_template('down.html')


# -----------------------------------------------------------------------------

if __name__ == '__main__':
    manager.run()
