#!/usr/bin/env python
import os
import tika
import jieba
import shutil
tika.initVM()
from tika import parser

class PatientParser:
    'Process the Chinese Patient Record'

    def __init__(self, dir, targetDir):
        self.dir = dir
        self.targetDir = targetDir

    # parse words via tika, and save as txt
    @staticmethod
    def tika_word(per, target, per_path):
        if per[:2] != "~$" and per[-4:] == ".doc" or per[-5:] == ".docx":
            print per
            new_file = os.path.join(target, per)
            new_file = new_file[:new_file.rfind(".")] + ".txt"
            if os.path.exists(new_file):
                return

            parsed = parser.from_file(per_path)
            content = parsed["content"]

            open(new_file, "w").write(content.encode("utf8"))

    @staticmethod
    def cut_txt(per, target, per_path):
        if per[-4:] == ".txt":
            print per
            new_file = os.path.join(target, per)
            new_file = new_file[:new_file.rfind(".")] + ".words"
            if os.path.exists(new_file):
                return

            seg_list = jieba.cut(open(per_path, 'r').read())
            words = "\n".join(seg_list)
            open(new_file, 'w').write(words.encode("utf8"))

    def search_dir(self, current, target, operation):
        for per in os.listdir(current):
            per_path = os.path.join(current, per)
            if os.path.isdir(per_path):
                if not os.path.exists(target):
                    os.mkdir(target)
                pert_dir = os.path.join(target, per)
                print per
                if not os.path.exists(pert_dir):
                    os.mkdir(pert_dir)

                self.search_dir(per_path, pert_dir, operation)

            elif os.path.isfile(per_path):
                operation(per, target, per_path)

    # convert doc into txt
    def convert2txt(self):
        print "begin convert into txt~ Please waiting ..."
        target = os.path.join(self.targetDir, "txts")
        print "txt files will be saved into 'txts' dir ~"
        if not os.path.exists(target):
            os.mkdir(target)

        self.search_dir(self.dir, target, operation = self.tika_word)

        print "Conversion has finished~"

    # cut text into words
    def cut2words(self, dict_path = "dict-v1.1.txt"):
        print "begin cut txt into words~ Please waiting ..."
        txt_dir = os.path.join(self.targetDir, "txts")
        if not os.path.exists(txt_dir):
            print "Please convert into txt first!!!!"
            print "Using the conver2txt() first~"
            return

        target = os.path.join(self.targetDir, "words")
        print "words files will be saved into 'words' dir ~"
        if not os.path.exists(target):
            os.mkdir(target)

        if os.path.exists(dict_path):
            jieba.load_userdict(dict_path)
        else:
            print "User's dict is ignored!"

        self.search_dir(txt_dir, target, operation = self.cut_txt)

        print "split words has finished~"

if __name__ == "__main__":
    pparser = PatientParser("./Grade_2016_12_08/", "./test/")
    #pparser.convert2txt()
    pparser.cut2words()