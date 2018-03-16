
import sqlite3,re
import jieba
con=sqlite3.connect('Music_data.db')
songs=con.execute("select * from song_list").fetchall()

def del_song_head():
    for song in songs:
        try: # 部分歌曲歌词缺失
            segment_by_line=song[2].split('\n')
        except:
            print('歌词缺失！')
            continue
        new_lyric=''
        for line in segment_by_line[1:]:
            if re.search('[作曲|作词]',line):
                print("已处理")
                continue
            new_lyric+=line+'\n'
        print("-----------------")
        con.execute("update song_list set lyric=? where song_id=? ", (new_lyric,song[0]))

for song in songs:
    try:
        seg_list=jieba.cut(song[2])
        lyric_segmented=' '.join(seg_list)
        con.execute("update song_list set lyric_segmented=? where song_id=? ", (lyric_segmented,song[0]))
    except:
        print('失败')
        continue
# print(",".join(seg_list))
print('over')
con.commit()
con.close()