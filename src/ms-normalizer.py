#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2018 Nick Kocharhook
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.

import os
import re
import pandas as pd
import argparse

def main():
	args = parseArguments()

	for path in args.paths:
		normalizer = Normalizer(path)
		normalizer.inPlace = args.inPlace

		# if normalizer.ready:
		normalizer.normalize()


def parseArguments():
	parser = argparse.ArgumentParser(description='Normalize MS openelections CSV files')
	parser.add_argument('--inPlace', dest='inPlace', action='store_true')
	parser.add_argument('paths', metavar='path', type=str, nargs='+',
					   help='path to a CSV file')

	return parser.parse_args()

class Normalizer(object):
	validColumns = ['county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes']
	partyMapping = {'Democrat': "DEM", "D": "DEM", "Republican": "REP", "R": "REP", "Libertarian": "LIB", "Reform": "REF", "Constitution": "CON", "Independent": "IND"}

	def __init__(self, path):
		self.path = path
		self.df = None
		self.inPlace = False

	def normalize(self):
		self.loadFileAtPath(self.path)

		if self.inPlace:
			self.writeFile(self.path)
		else:
			pathComponents = os.path.splitext(self.path)
			newPath = pathComponents[0] + '-normalized' + pathComponents[1]
			self.writeFile(newPath)

	def loadFileAtPath(self, path):
		print(path)
		self.df = pd.read_csv(path).dropna(how='all')

		invalidColumns = set(self.df) - set(Normalizer.validColumns)

		if invalidColumns:
			self.df = self.df.drop(columns=list(invalidColumns))

		# Drop rows with x/X for votes
		self.df = self.df.query('votes != "x" and votes != "X"')

		# Reorder columns
		self.df = self.df[Normalizer.validColumns]

		# Strip whitespace from all string columns
		self.df = self.df.applymap(lambda x: x.strip() if type(x)==str else x)

		# Normalize precinct column
		self.df['precinct'] = self.df['precinct'].str.replace(r' Precinct$', r'', regex=True)
		self.df['precinct'] = self.df['precinct'].str.replace(r'County Precinct', r'')
		self.df['precinct'] = self.df['precinct'].str.replace(r'TOTAL', r'Total')

		# Normalize party names
		self.df['party'] = self.df.loc[self.df['party'].notnull(), 'party'].replace(Normalizer.partyMapping)

		# Sort
		self.df = self.df.sort_values(Normalizer.validColumns)


	def writeFile(self, path):
		self.df.to_csv(path, index=False, na_rep='', float_format='%.f') # Format to avoid ".0" on the end of votes cells



# Default function is main()
if __name__ == '__main__':
	main()
