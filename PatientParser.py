#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import tika
import jieba

tika.initVM()
from tika import parser


class PatientParser:
    'Process the Chinese Patient Record'

    def __init__(self, dir, targetDir):
        self.dir = dir
        self.targetDir = targetDir

    # filter needless content within txt files
    @staticmethod
    def filter_txt(content):
        filter_content = ""
        word = ""
        per_key = ""
        key_num = 0
        key_list = []
        state = "Null"
        i = 0
        content_dict = {}
        null = re.compile("\s")
        number = re.compile("\d")

        content_length = len(content)
        while i < content_length:
            per = content[i]
            if state == "Null":
                if null.match(per) is None:
                    word = "".join([word, per])
                    state = "Word"

            elif state == "Word":
                if null.match(per) is None:
                    if per == u":" or per == u"：":
                        # condition: XXXX:(MMMM):
                        if (word[0] == u"(" or word[0] == u"（") and (word[-1] == u")" or word[-1] == u"）"):
                            per_key += word
                            state = "Key"

                        # not condition: http:// and 12:30
                        elif word[-4:] == "http" or number.match(word[-1]) != None:
                            word = "".join([word, per])
                        # condition: XXXX:
                        else:
                            per_key = word
                            state = "Key"

                    else:
                        word = "".join([word, per])
                else:
                    per_value = word
                    if per_key not in key_list:
                        key_list.append(per_key)
                        key_num += 1
                    content_dict.setdefault(key_num, []).append(per_value)

                    state = "Value"

            elif state == "Key":
                if null.match(per) is None:
                    word = per
                    state = "Word"

            elif state == "Value":
                if null.match(per) is None:
                    word = per
                    state = "Word"

            i += 1

        for i in range(0, key_num):
            key = "###key:" + key_list[i] + ":"
            value = "\n".join(content_dict[i+1])
            filter_content += key + "\n" + value + "\n\n"

        return filter_content

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

    # split text into words with jieba
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

    # search all dirs and files and do operation
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

        self.search_dir(self.dir, target, operation=self.tika_word)

        print "Conversion has finished~"

    # cut text into words
    def cut2words(self, dict_path="dict-v1.1.txt"):
        print "begin cut txt into words~ Please waiting ..."

        txt_dir = os.path.join(self.targetDir, "temp")
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

        self.search_dir(txt_dir, target, operation=self.cut_txt)

        print "split words has finished~"

    # extract features from words
    def extract_features(self):
        print "begin extract features from words~ Please waiting ..."

        target = os.path.join(self.targetDir, "features")
        # save intermediate results
        temp = os.path.join(self.targetDir, "temp")
        print "features files will be saved into 'features' dir ~"

        if not os.path.exists(target):
            os.mkdir(target)
        if not os.path.exists(temp):
            os.mkdir(temp)

        # copy words files into temp and remove blank characters within files
        # self.copy2temp(words_dir, temp)

        # select features from words


        print "Features extraction has finished~"

    # move words files from current_dir into target_dir
    def move_words(self, current_dir, target_dir):
        for per in os.listdir(current_dir):
            per_path = os.path.join(current_dir, per)
            if os.path.isdir(per_path):
                self.move_words(per_path, target_dir)

            elif os.path.isfile(per_path) and per[-4:] == ".txt":
                new_file = os.path.join(target_dir, per)

                content = open(per_path, 'r').read().decode("utf8")
                filter_content = self.filter_txt(content)

                open(new_file, 'w').write(filter_content.encode("utf8"))

    # copy words files into temp dir
    def copy2temp(self):
        txts_dir = os.path.join(self.targetDir, "txts")
        if not os.path.exists(txts_dir):
            print "Please convert into txt first!!!!"
            print "Using the conver2txt() first~"
            return
        temp = os.path.join(self.targetDir, "temp")
        if not os.path.exists(temp):
            os.mkdir(temp)

        print "filtered txt files will be saved into 'temp' dir ~"

        for per in os.listdir(txts_dir):
            per_path = os.path.join(txts_dir, per)
            if os.path.isdir(per_path):
                target_dir = os.path.join(temp, per)
                if not os.path.exists(target_dir):
                    os.mkdir(target_dir)
                self.move_words(per_path, target_dir)


if __name__ == "__main__":
    pparser = PatientParser("./Grade_2016_12_08/", "./test/")
    # pparser.convert2txt()
    # pparser.cut2words()
    # pparser.extract_features()
    pparser.copy2temp()
