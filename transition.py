# coding=utf-8

'''
This file is designed to help migrate the database while launching the new
student interface. If you are viewing this message, this means that this is
the commit that will launch the new site. Follow these instructions now:

1. COPY & PASTE THESE INSTRUCTIONS OUTSIDE OF THE REPO. They will disappear
   when you checkout a previous commit.

2. run `git checkout bc8d584`

3. run `python app.py db upgrade c2936ba298a0`

4. change the code in transition.py accordingly (b/c I am an idiot and its too
   complicated to change the code in previous commits):

   LINES 11-15
   ```
    if user.is_super_admin:
        user.role = 'super_admin'

    elif user.is_admin:
        user.role = 'admin'
   ```

5.  run `python transition.py`

6.  run `git checkout -- transition.py`

7.  run `git checkout master`

8.  run `python app.py db upgrade 8752f86d1e89`

Mission success. Hopefully.
'''

from app import db, get_status, Sentence, User


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
