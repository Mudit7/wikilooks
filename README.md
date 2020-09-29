# Wikilooks
A Search engine for Wikipedia Articles

### Required Python Libraries :

* ```xml.sax```
* ```nltk```
* ```Stemmer```

### Objectives :

Build a complete search engine by creating an Inverted Index on the Wikipedia Corpus ( of 2019 with size 57 GB), that gives you top k search results related to given query words.
The size of the inverted index created was about 13.5 GB
Two types of queries can be handled :

* Simple Queries : Ex. - ```5, young's modulus```
* Multi-field queries : Ex - ```3, b:V for Vendetta i:2006 ```

The search results are ordered in ranking using a weighted TF-IDF ranking based on occurrence of word in Title, Body, InfoBox and so on...
The first query returns top 5 results on "young's modulus" and second returns top 3 results on articles with "V for Vendetta" in the body and/or "2006" in infobox.

### How to run :


* Index Creation :
 ``` python index_creator.py <wikipedia_dump_path> <inverted_index_path>```

* Search :
	``` python search.py <inverted_index_path> <query_input_file>```


### Implementation Details :

* The main challenge is to create an Inverted Index for a huge dataset with a good tradeoff between the size of Inverted Index and time of index creation and the search time. The main Inverted Index created was around 13.x GB but I used 3 level indexing to make sure the index file loaded in the main memory at a time does not exceed 100 MB. The average search time for a single query with average length was about 5 seconds

Following Steps Follows to create Inverted Indexing :

* Parsing using ```xml.sax``` parser : Need to parse each page , title tag, infobox, body , category etc...
* Tokenization : Tokenize the doc to get each token using regular expression
* Casefolding : Case fold strings for caseless matching.
* Stop Words Removal : remove stop words which occur very frequently ```nltk.tokenize.wordpunct_tokenize```
* Stemming : get root/base word and store it ```pystemmer```
* A documentId to Title list for for easy retrieval of document title from posting lists.
* Inverted Index Creation : create positing lists word by word :
	*  ``` DocumentID : Title Frequency : Body Frequency : Infobox frequency : category frequency ```
* Create secondary indexes for cheap and efficient search retrieval

Firstly the Intermediate Index files like 0.txt,1.txt,2.txt,... and so on are created, then a K-way merge is performed to merge all these intermediate files into a single Index file. Each entry in the big Index file is a word along with its posting list. For quick retrieval of the Title's corresponding to a query I have created a Document ID - Title Mapping which can be loaded into the memory while performing the Search operation.
