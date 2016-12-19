#!/usr/bin/env python

import os
import tika
tika.initVM()
from tika import parser

class PatientParser:
    'Process the Chinese Patient Record'

    def __init__(self, dir, targetDir):
        self.dir = dir
        self.targetDir = targetDir

    def searchInDir(self, current, target):
        for per in os.listdir(current):
            perPath = os.path.join(current, per)
            if os.path.isdir(perPath):

                if not os.path.exists(target):
                    os.mkdir(target)
                pertDir = os.path.join(target, per)
                print per
                if not os.path.exists(pertDir):
                    os.mkdir(pertDir)

                self.searchInDir(perPath, pertDir)
            elif os.path.isfile(perPath):
                if per[:2] != "~$" and per[-4:] == ".doc" or per[-5:] == ".docx":
                    print per
                    newFile = os.path.join(target, per)
                    newFile = newFile[:newFile.rfind(".")] + ".txt"
                    if os.path.exists(newFile):
                        continue

                    parsed = parser.from_file(perPath)
                    content = parsed["content"]

                    open(newFile, "w").write(content.encode("utf8"))

    # convert doc into txt
    def convert2txt(self):
        print "begin convert into txt~ Please waiting ..."

        self.searchInDir(self.dir, self.targetDir)

        print "Conversion has finished~"

if __name__ == "__main__":
    pparser = PatientParser("./Grade_2016_12_08/", "./test/")
    pparser.convert2txt()