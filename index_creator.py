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
from nltk.tokenize import wordpunct_tokenize
nltk.download('stopwords')
stop_words = set(stopwords.words('english'))
from string import punctuation
stop_words.update(list(char for char in punctuation))
stemmer = Stemmer.Stemmer('english')
text_punc = list(punc for punc in punctuation if punc not in ['{', '}', '=', '[', ']' ])
text_punc.append('\n')
'''
The way I am performing indexing is:
firstly , temp files are created, each sorted in itself.
Now the indexes need to be merged, so we use k-way merge.
One thing to keep in mind is searching.
Assuming index is over 10gb and sorted, we can't really use binary search as that would require
a lot of memory to be loaded in MM in run time.
So we create an additional index of offsets where with each word in inverted index, its offset (in index_file)
will be stored. This brings down the load to certain extent. But its still too big. (in orders of 2 gb)
So we need another level of indexing. For every 100000 words in offset_file, we make a new file with the same
name as the first word. Now to look for the offset we just need to find the correct file. we now can easily
apply binary search and do so.
'''
def temp_write(Inverted_Index, file_ptr):
    value = list()
    for term in sorted(Inverted_Index):
        temp = term + ' '
        temp = temp + '|'.join(item for item in Inverted_Index[term])
        value.append(temp)
    if len(value):
        file_ptr.write('\n'.join(value).encode('utf-8').decode())

    file_ptr.close()


def index_write(words,inverted_index,index_file_path,offset_file_path,offset):
    items_to_write = list()
    offset_list = list()
    try:
        file_pointer = open(index_file_path, 'a+')
        file_pointer1 = open(offset_file_path, 'a+')
        for word in words:
            offset_term = word + ' ' + str(offset)
            word_text = word + ' '
            word_text = word_text + '|'.join(list(item for item in inverted_index[word]))
            offset_list.append(offset_term)
            items_to_write.append(word_text)
            offset = offset + len(word_text) + 1

        if len(offset_list):
            file_pointer1.write('\n'.join(offset_list).encode('utf-8').decode())
            file_pointer1.write('\n')

        if len(items_to_write):
            file_pointer.write('\n'.join(items_to_write).encode('utf-8').decode())
            file_pointer.write('\n')


        file_pointer.close()
        file_pointer1.close()
    except Exception as e:
        print("Error while opening the Index File. Exiting..")
    finally:
        file_pointer.close()
        file_pointer1.close()

    return offset


def K_Way_Merge(file_count,index_path):

    if not os.path.exists(index_path):
        try:
            os.makedirs(index_path)
        except OSError as e:
            if e.errno == errno.EEXIST:
                raise

    file_pointer = list()
    end_of_file = list()
    list_of_words = list()
    heap = list()

    for index in range(file_count):
        path_of_file = os.path.join('temp', str(index) + '.txt')
        file_pointer.append(open(path_of_file, 'r'))
        list_of_words.append(file_pointer[index].readline().split(' ', 1))
        if list_of_words[index][0] not in heap:
            heapq.heappush(heap,list_of_words[index][0])
        end_of_file.append(0)

    index_file_path = os.path.join(index_path, 'index_file' + '.txt')
    offset_file_path = "offset_file.txt"
    try:
        os.remove(index_file_path)
        os.remove(offset_file_path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise

    offset = 0
    flag = 0
    words = list()
    inverted_index = dict()
    while heap:
        top_most_word = heapq.heappop(heap)
        if top_most_word == "":
            continue
        words.append(top_most_word)
        if top_most_word not in inverted_index:
            inverted_index[top_most_word] = list()

        for index in range(file_count):

            if end_of_file[index] == 1:
                continue

            if list_of_words[index][0] == top_most_word:
                inverted_index[top_most_word].append(list_of_words[index][1].strip())
                list_of_words[index] = file_pointer[index].readline().split(' ', 1)

                if list_of_words[index][0] == "":
                    file_pointer[index].close()
                    end_of_file[index] = 1
                    continue

                if list_of_words[index][0] not in heap:
                    heapq.heappush(heap,list_of_words[index][0])

        if len(words)%100000 == 0:
            offset = index_write(words,inverted_index,index_file_path,offset_file_path,offset)
            flag = 1
            inverted_index = dict()
            words = list()

    if len(words):
        offset = index_write(words,inverted_index,index_file_path,offset_file_path,offset)




class Indexer(xml.sax.ContentHandler):

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
        self.eof = 1

    def title_processing(self,title_string):

        title_frequency = dict()
        title_string = re.sub('\\b[-\.]\\b', '', title_string)
        title_string = re.sub('[^A-Za-z0-9\{\}\[\]\=]+',' ', title_string)
        for each_word in wordpunct_tokenize(title_string):
            # each_word = each_word.lower()
            if each_word.lower() not in stop_words:
                each_word = stemmer.stemWord(each_word.lower())
                if each_word not in title_frequency:
                    title_frequency[each_word] = 0
                title_frequency[each_word]+= 1

        return title_frequency


    def text_processing(self,text_string):

        text_string = re.sub('[^A-Za-z0-9\{\}\[\]\=]+',' ', text_string)
        text_frequency = dict()

        regex_category = re.compile(r'\[\[Category(.*?)\]\]')
        table = str.maketrans(dict.fromkeys('\{\}\=\[\]'))

        new_text = regex_category.split(text_string)

        if len(new_text) > 1:
            for text in new_text[1:]:
                text = text.translate(table)
                for word in wordpunct_tokenize(text):
                    # word = word.lower()
                    if word.lower() not in text_frequency:
                        text_frequency[word.lower()] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                    text_frequency[word.lower()]['c'] += 1

            text_string = new_text[0]

        new_text = text_string.split('==External links==')
        if len(new_text) > 1:
            new_text[1] = new_text[1].translate(table)

            for word in wordpunct_tokenize(new_text[1]):
                # word = word.lower()
                if word.lower() not in text_frequency:
                    text_frequency[word.lower()] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word.lower()]['l'] += 1

            text_string = new_text[0]

        new_text = text_string.split("{{Infobox")

        braces_count = 1
        default_tag_type = 'i'

        if len(new_text) > 1:
            new_text[0] = new_text[0].translate(table)

            for word in wordpunct_tokenize(new_text[0]):
                # word = word.lower()
                if word.lower() not in text_frequency:
                    text_frequency[word.lower()] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word.lower()]['b'] += 1



            for word in re.split(r"[^A-Za-z0-9]+",new_text[1]):
                # word = word.lower()
                if "}}" in word.lower():
                    braces_count -= 1
                if "{{" in word.lower():
                    braces_count += 1
                    continue
                if braces_count == 0:
                    default_tag_type = 'b'

                word = word.lower().translate(table)

                if word not in text_frequency:
                    text_frequency[word] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word][default_tag_type] += 1


        else:
            text_string = text_string.translate(table)
            for word in wordpunct_tokenize(text_string):
                word = word.lower()
                if word.lower() not in text_frequency:
                    text_frequency[word.lower()] = dict(t=0,b=0,i=0,c=0,l=0,r=0)
                text_frequency[word.lower()]['b'] += 1


        duplicate_copy = dict()
        for term in text_frequency:
            stemmed_term = stemmer.stemWord(term)
            if stemmed_term not in duplicate_copy:
                duplicate_copy[stemmed_term] = text_frequency[term]
            else:
                for key in duplicate_copy[stemmed_term]:
                    duplicate_copy[stemmed_term][key] += text_frequency[term][key]

        text_frequency = dict()
        for term in duplicate_copy:
             if term not in stop_words or term != '':
                text_frequency[term] = duplicate_copy[term]

        return text_frequency


    def preprocessing(self,title,text):

        page_count = self.page_count
        title_frequency = self.title_processing(title)
        text_frequency = self.text_processing(text)
        file_pointer = open("DocId_Title_Map.txt",'a+')
        if self.first == 1:
            file_pointer.write('\n')

        if self.first == 0:
            self.first = 1

        value = str(page_count) + ' '+ title
        value = value.encode('utf-8').decode()

        for word_title in title_frequency:
            if word_title in text_frequency:
                text_frequency[word_title]['t'] += title_frequency[word_title]
            else:
                text_frequency[word_title] = dict(d= page_count,t=title_frequency[word_title],b=0,i=0,c=0,l=0,r=0)

        file_pointer.write(value)
        file_pointer.close()

        for term in text_frequency:
            if len(term) < 3 or term.startswith('0'):
                continue
            text_frequency[term]['d'] = str(page_count)
            if term not in self.inverted_index:
                self.inverted_index[term] = list()
            self.inverted_index[term].append(''.join(tag + str(text_frequency[term][tag]) for tag in text_frequency[term] if text_frequency[term][tag] != 0))


        if self.page_count%30000 == 0 or self.eof==1:
            file_name = os.path.join('temp',str(self.file_count) + '.txt')
            file_ptr = open(file_name, 'w+')
            temp_write(self.inverted_index,file_ptr)
            self.file_count = self.file_count + 1
            self.inverted_index = dict()
            self.eof = 0

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
        elif name == "mediawiki":
            self.eof = 1
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

def create_secondary_Index():
    if not os.path.exists('temp_offsets'):
        os.mkdir('temp_offsets')
    else:
        shutil.rmtree('temp_offsets')
        os.mkdir('temp_offsets')

    file_ptr = None
    with open('offset_file.txt') as offset_file:
        for lineno,line in enumerate(offset_file):
            if lineno % 10000 == 0:
                if file_ptr:
                    file_ptr = None
                value = line.strip().split(' ')[0]
                file_path = os.path.join('temp_offsets',value + '.txt')
                file_ptr = open(file_path,"w")
            file_ptr.write(line)
        if file_ptr:
            file_ptr.close()
    os.remove("offset_file.txt")


if __name__ == "__main__":

    # data_file = 'small.xml'
#     data_file = sys.argv[1]
    main_index_dir = 'inverted_index/'
    # durl = '/content/drive/My Drive/Phase2/'
    start = time.time()
    if not os.path.exists('temp'):
        os.makedirs('temp')

    if os.path.exists('DocId_Title_Map.txt'):
        os.remove('DocId_Title_Map.txt')

    xml_parser = xml.sax.make_parser()

    indexer = Indexer()
    xml_parser.setContentHandler(indexer)
    xml_parser.parse('small.xml')

    K_Way_Merge(indexer.file_count,main_index_dir)

    end = time.time()
    print("Time Taken to build an Inverted Index is : " + str(end - start) + " seconds")
    shutil.rmtree('temp')
    create_secondary_Index()
