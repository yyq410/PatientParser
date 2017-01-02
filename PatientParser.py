#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import re
import tika
from pyltp import Segmentor
from tika import parser
import argparse
import Levenshtein

parser = argparse.ArgumentParser(description="Process the patient records in outpaitent service")
parser.add_argument("-d", "--data", type=str, required=True, help="Specify the data directory")
parser.add_argument("-f", "--feature", type=str, required=True, help="Specify the important keys needed extracted")
parser.add_argument("-o", "--output", type=str, required=True, help="Specify the results directory")
parser.add_argument("-dict", "--dictionary", type=str, required=True, help="Specify the words dictionary")
parser.add_argument("-thres", "--threshold", type=str, default=0.5,
                    help="the min similarity when two keys are regarded as the same one")

args = parser.parse_args()


class PatientParser:
    'Process the Chinese Patient Record'
    # record the words parser
    seg_mentor = None
    # record the keys and files contain them in txt_dict dictionary
    txt_dict = {}
    # record the important keys
    features_list = []
    min_length = 4
    min_ratio = 0.6

    def __init__(self, dir, target_dir, dict_file, feature_file):
        # record the data dir
        self.dir = dir
        # record the results dir
        self.target_dir = target_dir
        # record the file number in data dir
        self.file_num = 0
        # the LTP words parsing
        PatientParser.seg_mentor = Segmentor()
        PatientParser.seg_mentor.load_with_lexicon("./ltp_data/cws.model", dict_file)
        self.feature_file = feature_file
        PatientParser.load_features(feature_file)

    # load import keys needed extracted
    @staticmethod
    def load_features(feature_file):
        pass

    # group keys according to the similarity
    @staticmethod
    def group_keys(keys_dict, threshold):
        keys = keys_dict.keys()
        # save results in dict(candidate word : [similar word1, similar word2, ...])
        group_keys = {}

        while len(keys) > 0:
            current = keys.pop()
            similar_keys = filter(lambda x: Levenshtein.ratio(x, current) > threshold, keys)
            for per in similar_keys:
                keys.remove(per)

            similar_keys.append(current)
            max_index = -1
            max_length = 0
            for per in range(len(similar_keys)):
                per_len = keys_dict[similar_keys[per]]
                if per_len > max_length:
                    max_length = per_len
                    max_index = per

            max_key = similar_keys[max_index]
            similar_keys.remove(max_key)
            group_keys[max_key] = similar_keys

        return group_keys

    # judge if is chinese
    @staticmethod
    def is_chinese(uchar):
        if u'\u4e00' <= uchar <= u'\u9fa5':
            return True
        else:
            return False

    # filter the () in the value (e.g.  (AAA)VVVV)
    @staticmethod
    def filter_bracket(value):
        if len(value) < 1:
            return value

        if value[0] == u"(":
            index = value.find(u")")

        if index != -1:
            ch_ratio = reduce(lambda x, y: x + y,
                              map(lambda x: PatientParser.is_chinese(x), [x for x in value[1:index]])) * 1.0 / (
                           index - 1)
            if ch_ratio >= PatientParser.min_ratio:
                value = value[(index + 1):]

        return value

    # condition AAA(BBB): , remove the (BBB)
    @staticmethod
    def filter_key(key):
        if len(key) > 0:
            final_char = key[-1]
            index = 0
            if final_char == u")":
                index = key.rfind(u"(")
            elif final_char == u"）":
                index = key.rfind(u"（")

            if index != 0:
                key = key[:index]

        return key

    # condition : AAA:BBB,AAA:
    @staticmethod
    def check_gap(word):
        gap_char = [u".", u";", u","]

        word_length = len(word)
        pos = word_length - 1
        is_bracket = False
        while pos > -1:
            if word[pos] in gap_char:
                break

            pos -= 1

        if word[pos] == u"," and len(word[:pos]) <= PatientParser.min_length:
            pos = -1

        pos2 = word.rfind(u"(")
        if pos2 != -1 and pos2 > pos:
            pos3 = word.rfind(u")")
            if pos3 == -1:
                is_bracket = True
                pos = pos2

        return [pos, is_bracket]

    # filter needless content within txt files
    @staticmethod
    def filter_txt(content, file_name):
        # convert chinese, SBC into DBC
        content = PatientParser.sbc2dbc(content)

        filter_content = ""
        word = ""
        per_key = ""
        key_num = 0
        key_list = []
        state = "Null"
        i = 0
        content_list = []
        line_skip = 0
        # when line_skip > skip_thres, set no key for the value
        skip_thres = 3

        # condition: AAA:(BBB)CCC  remove the (BBB)
        is_first = 1
        bracket_exist = 0
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
                    if per == u":":
                        # condition: XXXX:(MMMM):
                        if word[0] == u"(" and word[-1] == u")":
                            per_key += word
                            state = "Key"
                            line_skip = 0
                            is_first = 1
                            bracket_exist = 0

                        # not condition: http:// and 12:30
                        elif word[-4:] == "http" or number.match(word[-1]) is not None:
                            word = "".join([word, per])
                        # condition: XXXX:
                        else:
                            # check condition AAA:BBB[,.;(]AAA:BBB
                            [gap_position, is_bracket] = PatientParser.check_gap(word)
                            if gap_position != -1:
                                value_pre = word[:gap_position]

                                if bracket_exist:
                                    value_pre = PatientParser.filter_bracket(value_pre)
                                # when there are more 3 blank lines, no key (AAAAA:) for the value (BBBBBB)
                                # condition:
                                # AAAAA:
                                #
                                #
                                #
                                #      BBBBBB
                                if line_skip > skip_thres:
                                    per_key = ""

                                if len(value_pre) != 0:
                                    per_key = PatientParser.filter_key(per_key)

                                    if key_num > 0 and (len(per_key) == 0 and content_list[-1][0].startswith("NULL") \
                                                                or per_key == content_list[-1][0]):
                                        content_list[-1][1].append(value_pre)
                                    else:
                                        if len(per_key) == 0:
                                            per_key = "NULL" + str(key_num)
                                        key_num += 1
                                        key_list.append(per_key)
                                        content_list.append([per_key, [value_pre]])

                                    #print "key in gap: %s" % per_key.encode("utf8")
                                    #print "value in gap %s" % value_pre.encode("utf8")

                                word = word[(gap_position + 1):]

                            per_key = word
                            #print "key after gap: %s" % per_key.encode("utf8")
                            state = "Key"
                            line_skip = 0
                            is_first = 1
                            bracket_exist = 0
                    else:
                        word = "".join([word, per])
                else:
                    per_value = word
                    # condition AAA:(BBB)CCC
                    is_first = 0
                    blank_skip = 0

                    if bracket_exist:
                        per_value = PatientParser.filter_bracket(per_value)
                        bracket_exist = 0

                    # when there are more 3 blank lines, no key (AAAAA:) for the value (BBBBBB)
                    # condition:
                    # AAAAA:
                    #
                    #
                    #
                    #      BBBBBB
                    if line_skip > skip_thres:
                        per_key = ""
                    line_skip = 0

                    if len(per_value) != 0:
                        per_key = PatientParser.filter_key(per_key)
                        if key_num > 0 and (len(per_key) == 0 and content_list[-1][0].startswith("NULL") \
                                                    or per_key == content_list[-1][0]):
                            content_list[-1][1].append(per_value)
                        else:
                            if len(per_key) == 0:
                                per_key = "NULL" + str(key_num)
                            key_num += 1
                            key_list.append(per_key)
                            content_list.append([per_key, [per_value]])

                        #print "key in value: %s" % per_key.encode("utf8")
                        #print "value in value: %s" % per_value.encode("utf8")

                    state = "Value"

                    if per == "\n":
                        line_skip += 1

            elif state == "Key":
                if null.match(per) is None:
                    word = per
                    state = "Word"

                elif per == "\n":
                    line_skip += 1

                # test the condition: AAA:(BBB)CCC
                if is_first and per == u"(":
                    bracket_exist = 1

            elif state == "Value":
                if null.match(per) is None:
                    word = per
                    state = "Word"
                elif per == "\n":
                    line_skip += 1

            i += 1

        key_unique = list(set(key_list))
        for i in range(len(key_unique)):
            convert_key = key_unique[i]
            PatientParser.txt_dict.setdefault(convert_key, []).append(file_name)

        for i in range(0, key_num):
            key = "###key###\n" + key_list[i]
            value = "\n".join(content_list[i][1])
            filter_content += key + "\n###value###\n" + value + "\n\n"

        return filter_content

    # SBC to DBC
    @staticmethod
    def sbc2dbc(ustring):
        sentence = ""
        for uchar in ustring:
            int_code = ord(uchar)
            if int_code == 12288:
                int_code = 32
            elif 65281 <= int_code <= 65374:
                int_code -= 65248

            sentence += unichr(int_code)

        trans_words = ""
        in_tab = u"，。！？【】（）％＃＠＆１２３４５６７８９０"
        out_tab = u",.!?[]()%#@&1234567890"
        trans_dict = dict(zip(in_tab, out_tab))

        for per in sentence:
            if per in trans_dict.keys():
                trans_words += trans_dict.get(per)
            else:
                trans_words += per

        return trans_words

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

            seg_list = PatientParser.seg_mentor.segment(open(per_path, 'r').read())
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

        if not os.path.exists(self.target_dir):
            print "create the dir %s" % (self.target_dir)
            os.mkdir(self.target_dir)

        target = os.path.join(self.target_dir, "txts")
        print "txt files will be saved into 'txts' dir ~"

        if not os.path.exists(target):
            os.mkdir(target)

        self.search_dir(self.dir, target, operation=self.tika_word)

        print "Conversion has finished~"

    # cut text into words
    def cut2words(self, dict_path="dict-v1.1.txt"):
        print "begin cut txt into words~ Please waiting ..."

        temp_dir = os.path.join(self.targetDir, "temp")
        if not os.path.exists(temp_dir):
            print "Please filter txt files first!!!!"
            print "Using the () first~"
            return

        target = os.path.join(self.targetDir, "words")
        print "words files will be saved into 'words' dir ~"

        if not os.path.exists(target):
            os.mkdir(target)

        self.search_dir(temp_dir, target, operation=self.cut_txt)

        print "split words has finished~"

    # extract features from words
    def extract_features(self, threshold):
        print "begin extract features from words~ Please waiting ..."

        target = os.path.join(self.target_dir, "features")
        print "features files will be saved into 'features' dir ~"

        if not os.path.exists(target):
            os.mkdir(target)
        temp = os.path.join(self.target_dir, "temp")
        if not os.path.exists(temp):
            print "Please filter txt first !!!!"
            print "Using filter2temp() first~"
            return

        # group keys from extracted keys
        txt_keys_file = os.path.join(self.target_dir, "temp/txt_key.txt")
        if not os.path.exists(txt_keys_file):
            print "txt_key.txt not found in temp directory!!!!"
            print "Please use filter2temp() first~"
            return

        key_value_pair = [per.decode("utf8").split("\t") for per in open(txt_keys_file, 'r').readlines()]
        keys_dict = dict([(per[0][:-1], int(per[1].rstrip())) for per in key_value_pair])
        keys_group = PatientParser.group_keys(keys_dict, threshold)
        # save keys_group in the dir features
        keys_group_content = ""
        for key in keys_group:
            keys_group_content += key + "\t" + "\t".join(keys_group[key]) + "\n"
        open(os.path.join(target, "keys_group.txt"), 'w').write(keys_group_content.encode("utf8"))
        print "Similar keys are grouped into the features/keys_group.txt, you can check them~"

        # extract needed keys and values


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
                self.file_num += 1

                if os.path.exists(new_file):
                    return

                content = open(per_path, 'r').read().decode("utf8")
                filter_content = self.filter_txt(content, per)

                open(new_file, 'w').write(filter_content.encode("utf8"))

    # copy words files into temp dir
    def filter2temp(self):
        txts_dir = os.path.join(self.target_dir, "txts")
        if not os.path.exists(txts_dir):
            print "Please convert into txt first!!!!"
            print "Using the conver2txt() first~"
            return

        temp = os.path.join(self.target_dir, "temp")
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

        key_content = sorted(PatientParser.txt_dict.items(), key=lambda item: len(item[1]), reverse=True)
        key_text = ""
        key_text_more = ""
        for key, value in key_content:
            key_text += key + ":\t" + str(len(value)) + "\n"
            key_text_more += key + ":\t" + "\t".join(value).decode("utf8") + "\n"

        open(os.path.join(self.target_dir, "temp/txt_key.txt"), 'w').write(key_text.encode("utf8"))
        open(os.path.join(self.target_dir, "temp/txt_key_more.txt"), 'w').write(key_text_more.encode("utf8"))
        print "%d files have beed filtered~" % self.file_num
        print "all keys are saved in txt_key.txt~"
        print "filteration has finished~"


if __name__ == "__main__":
    pparser = PatientParser(args.data, args.output, args.dictionary, args.feature)
    # pparser.convert2txt()
    # pparser.filter2temp()
    # pparser.cut2words()
    pparser.extract_features(args.threshold)
