#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'this is test!'

from models import User, Blog, Comment

from transwarp import db

db.create_engine(user='www-data', password='www-data', database='test')

u = User(name='Test', email='test@example.org', password='123456789', image='about:blank')

u.insert()

print 'new user id:', u.id

u1 = User.find_first('where email=?', 'test@example.org')
print 'find user\'s name:', u1.name

u1.delete()

u2 = User.find_first('where email=?', 'test@example.org')
print 'find user:', u2