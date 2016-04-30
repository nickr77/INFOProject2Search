__author__ = 'Nick Roberts -- Steven Bock'

import re
import hashlib
import mechanize
import urlparse
import robotparser
from BeautifulSoup import BeautifulSoup
from tqdm import tqdm
import snowballstemmer
import math
browse = mechanize.Browser()
#GLOBAL VARS
baseUrl = "http://lyle.smu.edu/~fmoore/"
robots = robotparser.RobotFileParser()
robots.set_url(urlparse.urljoin(baseUrl, "robots.txt"))
robots.read()
urlList = [baseUrl]
visitedUrls = [baseUrl]
retrieveLimit = 0
stopWords = ()
outgoingLinks = []
badLinks = []
jpgAmount = 0
words = {}
docIDCounter = 1
documentIDs = []
duplicateDetect = []
duplicateCount = 0
stemmer = snowballstemmer.stemmer("english")
#END GLOBAL VARS
#---------- INPUT -----------
print "Welcome to the project 2 search engine"
temp = input("Please enter page crawl limit: ")
retrieveLimit = int(temp)
stopFile = open("stopwords.txt", "r")
lines = stopFile.read()
stopWords = lines.split()

def cosSim(doc, queryLen, docLen, queryIdf):
    temp = 0
    tempIndex = 0
    for x in doc:
        temp += (x*queryIdf[tempIndex])
        tempIndex += 1
    cosSimNumber = temp / (docLen * queryLen)
    return cosSimNumber


def rankResults(query, documentsByWord, docsToSearch, idfDict):
    cosSimList = []
    querylen = 0
    queryIdf = []
    docLengths = []
    termDocMatrix =  [] #words will be in order typed in query
    for document in docsToSearch:
        tempList = []
        for word in query:
            temp = 0
            for x in documentsByWord[word]: #looking at tuples

                if x[0] == document:
                    temp = x[1]
                    temp = temp * idfDict[word]
            tempList.append(temp)
        termDocMatrix.append(tempList)


    for word in query:
        querylen += pow(idfDict[word], 2)
        queryIdf.append(idfDict[word])
    querylen = math.sqrt(querylen)
    for doc in termDocMatrix:
        temp = 0
        for x in doc:
            temp = temp + pow(x, 2)
        temp = math.sqrt(temp)
        docLengths.append(temp)
    # print termDocMatrix
    # print docsToSearch
    # print queryIdf
    # print querylen
    # print docLengths
    docLenIndex = 0
    for x in termDocMatrix:
        cosSimList.append(cosSim(x, querylen, docLengths[docLenIndex], queryIdf))
        docLenIndex += 1
    resultList = zip(cosSimList, docsToSearch)
    resultList.sort()
    resultList.reverse()
    resultCount = 1
    resultLimit = 5
    for x in resultList:
        print resultCount, ". ", docIdDict[x[1]]
        resultCount += 1
        if resultCount >= resultLimit:
            break





def union(documents):
    union = []
    for x in documents.keys():
        for y in documents[x]:
            union.append(y[0])
    return set(union)

def idf(word):
    numberOfDocs = len(documentIDs)
    numberOfAppearances = len(words[word])
    idf = math.log((numberOfDocs/(numberOfAppearances)), 2)
    return idf




def getDocs(query):
    finalList = {}
    for word in query:
        tempList = []
        for x in words[word]:
            tempList.append(x)
        finalList[word] = tempList
    return finalList



def search(query):
    wordsToSearch = query.split()
    stemmedQuery = []
    idfDict = {}

    for x in wordsToSearch:
        stemmedQuery.append(stemmer.stemWord(x))

    finalQuery = []
    for x in stemmedQuery:
        if x in words.keys():
            finalQuery.append(x)
        else:
            print x, " was not not found"
    finalQuery = set(finalQuery)
    if len(finalQuery) == 0:
        print "No results"
        return;
    print "Searching for: ",
    for x in finalQuery:
        print x, " ",
        idfDict[x] = idf(x)
    print ""
    documentsByWord = getDocs(finalQuery)
    docsToSearch = union(documentsByWord)
    rankResults(finalQuery, documentsByWord, docsToSearch, idfDict)







print "Crawling Pages, please wait..."
with tqdm(total=retrieveLimit) as progress:
    for page in urlList:
        if docIDCounter > retrieveLimit:
            break #quits crawling if retrieval limit is reached
        try:
            #---------- Page Crawler (gets words and links from each page ---------
            soup = ""
            browse.open(page)
            if page.endswith(".txt"):
                soup = browse.response().read()
            else:
                soup = BeautifulSoup(browse.response().read()) #if can't parse, assumed to be binary file or 404
                soup = soup.getText()
            hashTest = hashlib.md5(soup.encode('utf-8')).hexdigest()
            if hashTest not in duplicateDetect:
                duplicateDetect.append(hashTest)
                wordsInPage = soup.split()
                if not page.endswith(".txt"):

                    for link in browse.links():
                        tempURL = urlparse.urljoin(link.base_url, link.url)
                        #BELOW: gets rid of duplicate urls resulting from index.html/index.htm
                        if tempURL.endswith("index.html"):
                            tempURL = tempURL.replace("index.html", "")
                        elif tempURL.endswith("index.htm"):
                            tempURL = tempURL.replace("index.htm", "")


                        if tempURL not in urlList:
                            if tempURL.startswith(baseUrl):
                                if robots.can_fetch("*", "/" + link.url): #checks robots.txt, necessary because of unusual robots.txt location
                                    urlList.append(tempURL)
                            else:
                                if tempURL + "/" not in urlList:
                                    outgoingLinks.append(tempURL)

                documentIDs.append((docIDCounter, page)) #if an exception hasn't happened by this point, it is safe to assign the docID
                progress.update(1)
                #-------------- WORD INDEXER ----------------#
                for x in wordsInPage: #parse and stem words, add to dictionary
                    x = x.replace(",", "") #removes commas before checking for stopwords
                    x = re.sub("[^a-zA-Z]","", x) #removes non-alphabetic characters from words
                    if x not in stopWords and len(x) > 0:
                        temp = x
                        temp = temp.lower()
                        temp = stemmer.stemWord(temp)
                        #print temp
                        if temp not in words.keys():
                            words[temp] = [(docIDCounter, 1)]
                        else:
                            tempPageList = [x[0] for x in words[temp]]
                            if docIDCounter in tempPageList:
                                tempIndex = tempPageList.index(docIDCounter)
                                words[temp][tempIndex] = (docIDCounter, words[temp][tempIndex][1] + 1)
                            else:
                                words[temp].append((docIDCounter,1))
                docIDCounter += 1 #increments doc ID after successful parsing
            #-------------- Binary File Handler ----------------#
            else:
                duplicateCount += 1

        except: #occurs if it is a binary file or non-existent file (this is needed for p2, below if statements are not
            #print page
            if page.endswith(".jpg"):
                jpgAmount += 1 #not needed for p2
            if browse.response().code == 404:
                badLinks.append(page)
    if (docIDCounter < retrieveLimit):
        progress.update(retrieveLimit - docIDCounter + 1)
############BEGIN PROJECT 2 Search Component  #################################
docIdDict = dict(documentIDs)
print ""
print "Web Crawling Complete, starting search engine"
searchQuery = ""
while True:
    searchQuery = raw_input("Please enter query words (separated by spaces) or type Quit: ")
    searchQuery = str(searchQuery)
    searchQuery = searchQuery.lower()
    if (searchQuery == "quit"):
        print "Goodbye!"
        break
    search(searchQuery)










#################################################################################











#-------------- Word Freqency Calculator ----------------#

# wordFreqency = []
# for x in words.keys():
#     totalTimes = 0
#     for y in words[x]:
#         totalTimes += y[1]
#     wordFreqency.append((str(x), totalTimes))
# frequentWords = sorted(wordFreqency, key=lambda x: x[1]) #Sorts by last value in tuple (frequency count)
# frequentWords.reverse()
# for x in frequentWords:
#     print x
# print duplicateDetect
# print badLinks
# print documentIDs
# print duplicateCount
# # for x in words:
# #     print x, " ", words[x]
# print urlList

# #--------------- Console Output ------------------# NOT USED ANYMORE
# print "Most Frequent Words: ", frequentWords[:20]
# print "OUTGOING LINKS: ",outgoingLinks #for debugging, remove once complete
# print "Good URLS: ",urlList
# print "BAD LINKS: ",badLinks
# print "JPEGS: ", jpgAmount
# print "DOCIDS : ", documentIDs - WILL NEED THIS IN PROJECT 2

# #---------FILE WRITING-------------#
# out = open('urlList.txt', 'w') #page List
# out.write('List of all urls visited (or at least attempted to):\n')
# for x in urlList:
#     out.write(x)
#     out.write("\n")
# out.close()
#
# out = open('outgoingLinks.txt', 'w') #outgoing links
# out.write('List of outgoing links:\n')
# for x in outgoingLinks:
#     out.write(x)
#     out.write("\n")
# out.close()
#
# out = open('badLinks.txt', 'w') #bad links
# out.write('List of bad links:\n')
# for x in badLinks:
#     out.write(x)
#     out.write("\n")
# out.close()
#
# out = open('jpegAmount.txt', 'w') #amount of jpegs
# out.write("JPEG AMOUNT: ")
# out.write(str(jpgAmount))
# out.close()
#
# out = open('wordIndex.txt', 'w') #amount of jpegs
# out.write("Word Index:\n")
# for x in words.keys():
#     out.write(x)
#     out.write(": ")
#     out.write(str(words[x]))
#     out.write('\n')
# out.close()
#
# out = open('frequentWords.txt', 'w')
# out.write("20 most frequent words and amount of occurences:\n")
# for x in frequentWords[:20]:
#     out.write(x[0])
#     out.write(": ")
#     out.write(str(x[1]))
#     out.write('\n')
# out.close()
