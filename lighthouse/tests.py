#!/usr/bin/python

import unittest

import data

class TestData(unittest.TestCase):

	def test_init(self):
		d = data.Data()
		self.assertIsNotNone( d.data)

	def test_load(self):
		d = data.Data()
		r = d.load( '10')
		self.assertTrue( r)
		self.assertEquals( 10, d.data)
		r = d.load( '"a"')
		self.assertTrue( r)
		self.assertEquals( 'a', d.data)
		r = d.load( '{"a":1,"b":"x","c":[1,2]}')
		self.assertTrue( r)
		self.assertIsNotNone( d.data)

		r = d.load( '{"a":1')
		self.assertFalse( r)

	def test_traverse(self):
		# TODO
		pass

	
