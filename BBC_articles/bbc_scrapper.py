from selenium import webdriver
import time 
import urllib
import pandas as pd
from selenium.webdriver.common.by import By
from flair.models import TextClassifier
from flair.tokenization import SegtokSentenceSplitter
from flair.models import SequenceTagger
import nltk
import re
import matplotlib.pyplot as plt
import spacy
import networkx as nx

class WebMine():
    
    def __init__(self, df):
        # initialize with already existing dataframe
        self.df = df
        
    def get_links(self,url,xpath):
        
        driver = webdriver.Chrome()
        driver.get(url)
        my_Xpath = xpath
        all_elements = driver.find_elements(By.XPATH, my_Xpath)

        # Fetch and store the links
        links = []
        for element in all_elements:
            links.append(element.get_attribute('href'))
        
        return links
    
    
    def get_author_name(self,driver,dict_link):
        my_Xpath_author = ".//p[contains(@class,'ssrcss-1rv0moy-Contributor')]"
        all_elements = driver.find_elements(By.XPATH, my_Xpath_author)
        if(len(all_elements)==0):
            print("no author detected!!")
        elif(len(all_elements)>1):
            print('Detected more than 1 authors!')
        else:
            author_name = all_elements[0].text
            dict_link['author'] = author_name 
        return dict_link
    
    
    def get_heading(self,driver,dict_link):
        all_elements = driver.find_elements(By.ID, 'main-heading')
        if(len(all_elements)==0):
            print("detected no heading!!")
        elif(len(all_elements)>1):
            print('Detected more than 1 Heading!')
        else:
            heading = all_elements[0].text
            dict_link['heading'] = heading 
        return dict_link
    
    
    def get_text(self,driver,dict_link):
        text = ''
        my_Xpath_text = "//div[contains(@data-component,'text-block')]"
        all_elements = driver.find_elements(By.XPATH, my_Xpath_text)
        if(len(all_elements)==0):
            print('No text found!!')
            dict_link['text'] = text
        else:
            for i in range(len(all_elements)):
                text = text + all_elements[i].text
                dict_link['text'] = text
        return dict_link
    
    def get_image(self,driver,dict_link,link,itr):
        my_Xpath_img = "//img[contains(@class,'ssrcss-1drmwog-Image')]"
        all_elements = driver.find_elements(By.XPATH, my_Xpath_img)
        if(len(all_elements)==0):
            print('No images found on webpage')
        else:
            url_list = []
            caption_list = []
            loc_list = []
            for i in range(len(all_elements)):
                url_list.append(all_elements[i].get_attribute('src'))
                caption_list.append(all_elements[i].get_attribute('alt'))
                loc_list.append("Images/link_"+str(itr)+"_image_"+str(i)+".jpg")
                urllib.request.urlretrieve(url_list[-1], loc_list[-1])
            dict_link['img_url'] = url_list
            dict_link['img_caption'] = caption_list
            dict_link['img_loc'] = loc_list
        return dict_link
    
    def get_time(self,driver,dict_link):
        time_element = driver.find_elements(By.XPATH, "//time[@data-testid='timestamp']")
        if(len(time_element)==0):
            print("no timestamp found!!")
        elif(len(time_element)>1):
            print('Detected more than 1 timestamps!')
            dict_link['date'] = time_element[0].get_attribute('datetime')[:10]
        else:
            dict_link['date'] = time_element[0].get_attribute('datetime')[:10]
        return dict_link
    
    def get_page_df(self,links):

        driver = webdriver.Chrome()
        # Loop through all the links and launch one by one
        
        itr = 0
        for link in links:
            print("scraping: ",link)
            
            # check if link has already been scraped before
            if link in self.df.values:
                print("link already exists")
                continue
            
            # store attributes in a dict and append to df in the end
            dict_link = {}
            
            # open link
            driver.get(link)
            dict_link['page_url'] = link
            
            # get author name 
            dict_link = self.get_author_name(driver,dict_link)           
            # get heading
            dict_link = self.get_heading(driver,dict_link)            
            # get text
            dict_link = self.get_text(driver,dict_link)                  
            # get image
            dict_link = self.get_image(driver,dict_link,link,itr)            
            # get time
            dict_link = self.get_time(driver,dict_link)
            
            # get sentiment and NER
            if(dict_link['text']!=''):
                sentiment, ner_tag_dict = self.get_NER_Sent(dict_link['text'])
                dict_link['text_sentiment'] = sentiment
                dict_link['NER' ] = ner_tag_dict
            
            time.sleep(5)
            self.df = self.df.append(dict_link, ignore_index=True)
            
            itr = itr+1
            
        return
    
    # get sentiment of field in df. field can be title or heading
    def get_NER_Sent(self,text):

        # add space after period where it does not exist, required to distinct them as separate sentences
        text = re.sub(r'\.(?=[^ \W\d])', '. ', text)

        # initialize sentence splitter
        splitter = SegtokSentenceSplitter()

        # use splitter to split text into list of sentences
        try:
            sentences = splitter.split(text)
        except:
            print("sentence could not be split")
            print(text)

        # load tagger call predict
        classifier = TextClassifier.load('sentiment')
        classifier.predict(sentences)

        # predict tags for sentences
        tagger = SequenceTagger.load('ner')
        tagger.predict(sentences)

        ner_tag_dict = {}
 
        # iterate through sentences and print predicted labels
        sentiment = 0
        for s in sentences:
            sentiment =  sentiment + s.labels[0].score * (-1,1)[str(s.labels[0]).split()[0].startswith("POS")]

            s_dict = s.to_dict(tag_type='ner')

            for idx in range(len(s_dict['entities'])):
                entity_text = s_dict['entities'][idx]['text']
                for idx2 in range(len(s_dict['entities'][idx]['labels'])):
                    entity_dict = s_dict['entities'][idx]['labels'][idx2].to_dict()
                    entity_name = entity_dict['value']
                    entity_conf = entity_dict['confidence']
                    if(entity_conf>0.8):
                        if entity_name not in ner_tag_dict:
                            ner_tag_dict[entity_name] = [entity_text]
                        else:
                            ner_tag_dict[entity_name].append(entity_text)

        sentiment = sentiment/len(sentences)
        return sentiment,ner_tag_dict
    
if __name__ == "__main__":
    
    # try loading df, if unsuccesful create empty df
    try:
        df = pd.read_csv("bbc_df.csv")
    except:
        cols = ['page_url','author','date','heading','text','text_sentiment','NER','img_caption','img_url','img_loc']
        df = pd.DataFrame(columns=cols)

    bbc = WebMine(df)
    
    # get links
    news_links = bbc.get_links("https://www.bbc.co.uk/news/science-environment-56837908","//a[contains(@class,'gs-c-promo-heading gs-o-faux-block-link')]")
    
    # update df with infor on new links
    bbc.get_page_df(news_links)

    bbc.df = bbc.df[bbc.df.columns.drop(list(bbc.df.filter(regex='Unnamed')))]
    
    # drop duplicates
    bbc.df = bbc.df.drop_duplicates(subset='page_url')
    bbc.df.reset_index(drop=True, inplace=True)

    # saving the dataframe
    bbc.df.to_csv('bbc_df.csv')
    