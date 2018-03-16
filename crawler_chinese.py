from urllib import request
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import sqlite3
import re
import json

class crawler:
    def __init__(self,playList_url,table_name,dbname='Music_data_chinese.db'):
        self.url=playList_url
        self.con=sqlite3.connect(dbname)
        self.table_name=table_name
        self.create_table(table_name)
        self.headers = {
            'Referer': 'http://music.163.com/',
            'Host': 'music.163.com',
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:38.0) Gecko/20100101 Firefox/38.0 Iceweasel/38.3.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
        }
    def get_all_pages(self):
        pages=[]
        nextPage=self.get_next_page(self.url)

        while nextPage:
            pages.append(nextPage)
            nextPage=self.get_next_page(nextPage)

        return pages

    def get_next_page(self,url):
        try:
            page = request.urlopen(url)
        except:
            print("Counld not open %s " % url)
        soup = BeautifulSoup(page.read(),'lxml')
        try:
            nextPage = soup.find('a', class_='zbtn znxt')['href']
            nextPage = "http://music.163.com" + nextPage
        except:
            nextPage = None
            print("Could not find next page for %s,\t maybe has over!" % url)
        return nextPage

    '''
        获取所有页面中的歌单，并存入数据库
        done
    '''
    def get_playList(self):
        print("Start:\n\t爬取当前类别歌单列表 ...\n")
        pages=self.get_all_pages()
        playList_links_all=[]
        for page in pages:
            try:
                page=request.urlopen(self.url)
            except:
                print("Counld not open %s " % self.url)

            soup=BeautifulSoup(page.read(),'lxml')
            playList_links=soup.find_all('a',class_='msk')

            # 需要从html标签中提取url
            play_list_url=[]
            for play_list in playList_links:
                play_list_url.append(play_list['href'])
            playList_links_all.extend(play_list_url)
        print("Successfully: \t歌单爬取完毕!"
              "\n\tPlay list counts:",len(playList_links_all))
        return playList_links_all

    '''
        获取某个歌单中的所有歌曲链接
        down
    '''
    def get_musics_in_playList(self):

        play_lists=self.get_playList()
        print("Start:开始爬取歌曲列表...")
        song_counts = 0
        s = requests.session()
        for playList_url in play_lists:
            try:
                playList_url='http://music.163.com'+playList_url
                print('url:',playList_url)
                page= s.get(playList_url,headers=self.headers)
            except:
                print("Counld not open %s " % playList_url)

            soup=BeautifulSoup(page.content)
            song_links=soup.find_all('a' , href = re.compile("^/song\?id=[0-9]+"))
            for link in song_links:
                if link.has_attr('class'):
                    continue
                # print('link:',link)
                songId=int(re.search("[0-9]+$",link['href']).group())
                # print('songid:',songId)
                if self.con.execute("select * from {} where song_id={}".format(self.table_name,songId)).fetchone():
                    # print('歌曲已存在，ID：%d' % songId)
                    continue
                self.con.execute("insert into song_list_chinese(song_id,song_name) values(?,?)",(songId,link.string))

                song_counts+=1

                if song_counts!=0 and song_counts%300==0:
                    print('已获取歌曲数量：',song_counts)
        self.con.commit()
        print("Successfully：歌曲爬取完毕,已存入数据库！歌曲数量：",song_counts)

    '''
        获取某歌曲的歌词内容
    '''
    def get_lyric_in_music(self):
        # self.get_musics_in_playList()
        print("Start : 开始爬取歌词内容...")
        song_list = self.con.execute("select song_id from %s " % self.table_name).fetchall()
        song_counts = 0

        for songUrl in song_list:
            try:
                lyric_url = 'http://music.163.com/api/song/lyric?' + 'id=' + str(songUrl[0]) + '&lv=1&kv=1&tv=-1'
                # s = requests.session()
                # page = s.get(songUrl, headers=self.headers)
                lyric=requests.get(lyric_url)
                json_obj=lyric.text
                j=json.loads(json_obj)
            except:
                print("Counld not open %s " % lyric_url)
            try:
                lrc=j['lrc']['lyric']
                pat = re.compile(r'\[.*\]')  # 下面这三行正则匹配删除时间轴
                lrc = re.sub(pat, "", lrc)
                lrc = lrc.strip()
                # self.con.execute("update {} set lyric='{}' where song_id={}".format(self.table_name,lrc,songUrl[0]))
                # 由于部分歌词中存在 '、''问题，所以上一种情况可能会导致语法错误从，又因为sql中只有values可用？占位符，表名不可以，所以手动写上表名
                self.con.execute("update  song_list_chinese set lyric=? where song_id=?" ,(lrc,songUrl[0]))
                song_counts+=1
            # 之前当出现异常时except中输出lrc，怀疑输出的是之前上一次循环的lrc，本次的lrc由于关键字错误（不存在lrc）未创建成功？？待排查！！
            except KeyError as e:
                pass
            if song_counts!=0 and song_counts%200==0:
                print("已爬取歌词：%d.." % song_counts)
        self.con.commit()
        self.con.close()
        print("Successfully:歌词爬取完毕！")

    '''
        创建相关表
        done
    '''
    def create_table(self,table_name):
        print("创建数据表：%s ..." % table_name)
        self.con.execute('create table if not exists %s(song_id Integer primary key,'
                         'song_name Text,lyric Text,lyric_segmented text )' % table_name)
        self.con.commit()
        print("创建完毕!")

if __name__ =='__main__':
    url = 'http://music.163.com/discover/playlist/?cat=%E5%8D%8E%E8%AF%AD'
    table_name="song_list_chinese"
    crawler=crawler(url,table_name=table_name)
    crawler.get_lyric_in_music()