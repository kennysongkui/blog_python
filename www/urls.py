#!/usr/bin/env python
# -*- coding: utf-8 -*-

__author__ = 'This is test.'

import os, re, time, base64, hashlib, logging

from transwarp.web import get, post, ctx, view, interceptor, seeother, notfound

from apis import api, APIError, APIValueError, APIPermissionError, APIResourceNotFoundError

from models import User, Blog, Comment
from config import configs

__COOKIE_NAME = 'awesession'
__COOKIE_KEY = configs.session.secret

def make_signed_cookie(id, password, max_age):
	# build cookie string by: id-expires-md5
	expires = str(int(time.time() + (max_age or 96400)))
	L = [id, expires, hashlib.md5('%s-%s-%s-%s' % (id, password, expires, __COOKIE_KEY)).hexdigest()]
	return '-'.join(L)

def parse_signed_cookie(cookie_str):
	try:
		L = cookie_str.split('-')
		if len(L) != 3:
			return None
		id, expires, md5 = L
		if int(expires) < time.time():
			return None
		user = User.get(id)
		if user is None:
			return None
		if md5 != hashlib.md5('%s-%s-%s-%s' % (id, user.password, expires, __COOKIE_KEY)).hexdigest():
			return None
		return user
	except:
		return None
	
def check_admin():
	user = ctx.request.user
	if user and user.admin:
		return
	raise APIPermissionError('No Permission.')

@interceptor('/')
def user_interceptor(next):
	logging.info('try to bind user from session cookie...')
	user = None
	cookie = ctx.request.cookies.get(__COOKIE_NAME)
	if cookie:
		logging.info('parse session cookie...')
		user = parse_signed_cookie(cookie)
		if user:
			logging.info('bind user <%s> to session...' % user.email)
	ctx.request.user = user
	return next()

@interceptor('/manage/')
def manage_interceptor(next):
	user = xtx.request.user
	if user and user.admin:
		return next()
	raise seeother('/signin')

@view('blogs.html')
@get('/')
def index():
	blogs = Blog.find_all()
	return dict(blogs=blogs, user=ctx.request.user)

@view('signin.html')
@get('/signin')
def signin():
	return dict()

@get('/signout')
def signout():
	ctx.response.delete_cookie(_COOKIE_NAME)
	raise seeother('/')

@api
@post('/api/authenticate')
def authenticate():
	i = ctx.request.input(remember='')
	email = i.email.strip().lower()
	password = i.password
	remember = i.remember
	user = User.find_first('where email=?', email)
	if user is None:
		raise APIError('auth:failed', 'email', 'Invalid email.')
	elif user.password != password:
		raise APIError('auth:failed', 'password', 'Invalid password.')
	# make session cookie:
	max_age = 604800 if remember=='true' else None
	cookie = make_signed_cookie(user.id, user.password, max_age)
	ctx.response.set_cookie(_COOKIE_NAME, cookie, max_age=max_age)
	user.password = '******'
	return user
	
@api
@get('/api/users')
def api_get_users():
	users = User.find_by('order by create_at desc')
	for u in users:
		u.password = '******'
	return dict(users=users)