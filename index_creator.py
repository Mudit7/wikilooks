import xml.sax.handler
import nltk
import heapq
import time
import sys
import shutil
import errno
from nltk.corpus import stopwords
import Stemmer
from copy import deepcopy
import os
import re
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
from string import punctuation
stop_words.update(list(char for char in punctuation))
stemmer = Stemmer.Stemmer('english')
text_punc = list(punc for punc in punctuation if punc not in ['{', '}', '=', '[', ']' ])
text_punc.append('\n')
ntokens = 0

class CreateIndex(xml.sax.ContentHandler):

    def __init__(self):

        self.istitle = False
        self.istext = False
        self.isfirstid = False
        self.isid = False
        self.title = ""
        self.text = ""
        self.docid = ""
        self.inverted_index = dict()
        self.page_count = 0
        self.file_count = 0
        self.first = 0

    def title_processing(self,title):

        title_frequency = dict()
        title = re.sub('\\b[-\.]\\b', '', title)
        title = re.sub('[^A-Za-z0-9\{\}\[\]\=]+',' ', title)
        for word in nltk.tokenize.wordpunct_tokenize(title):
            word = word.lower()
            if word not in stop_words:
                stemmedword = stemmer.stemWord(word)
                if stemmedword not in title_frequency:
                    title_frequency[stemmedword] = 1
                else:
                    title_frequency[stemmedword]+= 1

        return title_frequency


    def text_processing(self,text_string):

        text_string = re.sub('[^A-Za-z0-9\{\}\[\]\=]+',' ', text_string)
        text_frequency = dict()
        table = str.maketrans(dict.fromkeys('\{\}\=\[\]'))
        splitted_text = re.split(r'\[\[Category(.*?)\]\]',text_string)
        if len(splitted_text) > 1:
            for text in splitted_text[1:]:
                text = text.translate(table)
                for word in nltk.tokenize.wordpunct_tokenize(text):
                    word = word.lower()
                    if word not in text_frequency:
                        text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                    text_frequency[word]['c'] += 1
            text_string = splitted_text[0]

        splitted_text = text_string.split('==External links==')
        if len(splitted_text) > 1:
            splitted_text[1] = splitted_text[1].translate(table)

            for word in nltk.tokenize.wordpunct_tokenize(splitted_text[1]):
                word = word.lower()
                if word not in text_frequency:
                    text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word]['l'] += 1

            text_string = splitted_text[0]

        splitted_text = text_string.split("{{Infobox")

        braces_count = 1
        default_tag_type = 'i'

        if len(splitted_text) > 1:
            splitted_text[0] = splitted_text[0].translate(table)

            for word in nltk.tokenize.wordpunct_tokenize(splitted_text[0]):
                word = word.lower()
                if word not in text_frequency:
                    text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word]['b'] += 1

            for word in re.split(r"[^A-Za-z0-9]+",splitted_text[1]):
                word = word.lower()
                if "}}" in word:
                    braces_count -= 1
                if "{{" in word:
                    braces_count += 1
                    continue
                if braces_count == 0:
                    default_tag_type = 'b'

                word = word.translate(table)

                if word not in text_frequency:
                    text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word][default_tag_type] += 1


        else:
            text_string = text_string.translate(table)
            for word in nltk.tokenize.wordpunct_tokenize(text_string):
                word = word.lower()
                if word not in text_frequency:
                    text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word]['b'] += 1

        for word in text_frequency.keys():
            global ntokens
            ntokens += (text_frequency[word]['t']+text_frequency[word]['b']+text_frequency[word]['i']+text_frequency[word]['c']+text_frequency[word]['l']+text_frequency[word]['r'])


        processed_words = dict()
        for term in text_frequency:
            if term not in stop_words or term != '':
                stemmed_term = stemmer.stemWord(term)
                if stemmed_term not in processed_words:
                    processed_words[stemmed_term] = text_frequency[term]
                else:
                    for key in processed_words[stemmed_term]:
                        processed_words[stemmed_term][key] += text_frequency[term][key]

        return processed_words


    def preprocessing(self,title,text):

        page_count = self.page_count
        title_frequency = self.title_processing(title)
        text_frequency = self.text_processing(text)

        if self.first == 0:
            self.first = 1

        value = str(page_count) + ' '+ title
        value = value.encode('utf-8').decode()

        for word_title in title_frequency:
            if word_title in text_frequency:
                text_frequency[word_title]['t'] += title_frequency[word_title]
            else:
                text_frequency[word_title] = dict(d= page_count,t=title_frequency[word_title],b=0,i=0,c=0,l=0,r=0)

        for term in text_frequency:
            if len(term) < 3 or term.startswith('0'):
                continue
            text_frequency[term]['d'] = str(page_count)
            if term not in self.inverted_index:
                self.inverted_index[term] = list()
            self.inverted_index[term].append(''.join(tag + str(text_frequency[term][tag]) for tag in text_frequency[term] if text_frequency[term][tag] != 0))


    def startElement(self,name,attribute):

        if name == "title":
            self.istitle = True
            self.title = ""
        elif name == "text":
            self.istext = True
            self.text = ""
        elif name == "page":
            self.isfirstid = True
            self.docid = ""
        elif name == "id" and self.isfirstid:
            self.id = True
            self.isfirstid = False

    def endElement(self,name):

        if name == "title":
            self.istitle = False
        elif name == "text":
            self.istext = False
        elif name == "id":
            self.isid = False
            #self.isfirstid = False ## Changeable Areas
        elif name == "page":
            self.page_count = self.page_count + 1
            text = deepcopy(self.text)
            title = deepcopy(self.title)
            self.preprocessing(title,text)


    def characters(self, content):

        if self.istitle:
            self.title = self.title + content
        elif self.istext:
            self.text = self.text + content
        elif self.isid:
            self.docid = self.docid + content

def search(query):
    arr = [ i.start() for i in re.finditer(':', query)]
    if len(arr)==0:
        #simple query
        words = query.split(' ')
        for word in words:
            index_ptr = open('index_file','r')
            for line in index_ptr.readlines():
                line = line.strip().split(' ', 1)
                if word == line[0]:
                    postings = line[1].split('|')
                    for posting in postings:
                        print(posting[posting.index('d')+1:])

    else:
        querymap = {}
        for i in range(len(arr)):
            if i == len(arr)-1:
                end = len(query)
            else:
                end = arr[i+1]-2
            querymap[query[arr[i]-1]] = query[arr[i]+1 : end].strip()

        print(querymap)

        for item in querymap.items():
            # index_ptr = open('/Users/mudit/Wiki/2019201063/inverted_index/index_file','r')
            index_ptr = open(sys.argv[1]+'/index_file','r')
            for line in index_ptr.readlines():
                line = line.strip().split(' ', 1)
                if item[1] == line[0]:
                    postings = line[1].split('|')
                    for posting in postings:
                        if item[0] in posting:
                            print(posting[posting.index('d')+1:])

def make_index(stat_file,index_path,index_dict):
    if not os.path.exists(index_path):
        try:
            os.makedirs(index_path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise

    value = list()
    file_pointer = open(os.path.join(index_path,'index_file'), 'w+')
    for term in index_dict:
        temp = term + ' '
        temp = temp + '|'.join(item for item in index_dict[term])
        value.append(temp)
    if len(value):
        file_pointer.write('\n'.join(value).encode('utf-8').decode())
    file_pointer.close()

    statfile_pointer = open(stat_file,'w+')
    statfile_pointer.write(str(ntokens)+'\n')
    statfile_pointer.write(str(len(index_dict)))

start = time.time()
xml_parser = xml.sax.make_parser()
Indexer = CreateIndex()
xml_parser.setContentHandler(Indexer)

xml_parser.parse(sys.argv[1])
make_index(sys.argv[3], sys.argv[2], Indexer.inverted_index)
end = time.time()
print("Time Taken for indexing = " + str(end - start) + " sec")
