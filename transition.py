# coding=utf-8

from app import db, get_status, Sentence, User

# python app.py db upgrade c2936ba298a0
# python transition.py

for user in User.query.all():

    # transition existing user roles
    if user.is_admin:
        user.role = 'admin'

    elif user.is_super_admin:
        user.role = 'super_admin'

    else:
        user.role = 'annotator'

    # generate statuses
    user.generate_statuses()

    db.session.add(user)

    # transition existing statuses
    for sentence in Sentence.query.filter(Sentence.annotators != {}).all():
        old_status = sentence.annotators.get(user.id)

        if old_status:
            new_status = get_status(sentence.id, user.id)

            if old_status:
                new_status.status = 'annotated'

            # note that if old_status == '', then it is 'unannotated', which is
            # set by default
            elif old_status is None or old_status is False:
                new_status.status = 'in-progress'

            db.session.add(new_status)

db.session.commit()
