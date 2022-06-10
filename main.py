# from dotenv import load_dotenv

import os
from io import BytesIO
import sys
from requests import get as GET
from os import path
import locale
from pathlib import Path
import pytz
from time import sleep


from datetime import date, datetime, timedelta

import tweepy
from PIL import Image, ImageDraw, ImageFont
from timeout_decorator import timeout
import io,sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# .envファイルの内容を読み込見込む
# load_dotenv('.env')

# CONSUMER_KEY = os.environ["CONSUMER_KEY"]
# CONSUMER_SECRET = os.environ["CONSUMER_SECRET"]
# ACCESS_TOKEN = os.environ["ACCESS_TOKEN"]
# ACCESS_TOKEN_SECRET = os.environ["ACCESS_TOKEN_SECRET"]
CONSUMER_KEY = os.environ.get("CONSUMER_KEY")
CONSUMER_SECRET = os.environ.get("CONSUMER_SECRET")
ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.environ.get("ACCESS_TOKEN_SECRET")
FONT_PATH = Path("./static/RictyDiminished-Regular.ttf")
# font = ImageFont.load_default()
IMG_PATH = Path("/tmp/out_img.jpg")

#設定
#時間
aimed_hour = 12
#分
aimed_minute = 35
#賞金
prize = str(1)

def getFollowers_ids(api):
    followers_ids = tweepy.Cursor(api.get_follower_ids).items()
    # print(followers_ids)
    # print("=======")
    # followerIDs = api.get_follower_ids(id= Id)
    followers_ids_list = []
    # for followers_id in followers_ids:
    for followers_id in followers_ids:
        followers_ids_list.append(followers_id)

    # print(followers_ids_list)

    return followers_ids_list


class Listener(tweepy.Stream):
    def __init__(self,CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET, status_list, api):
        super().__init__(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET)
        self.status_list = status_list
        self.api = api

    def on_status(self, status):
        #11分を過ぎたものがでてきたらフィニッシュ
        if status.created_at.minute > aimed_minute + 11:
            sys.exit()
        try:
            record = [s for s in self.status_list if s.author.id == status.author.id][0]
            if status.user.id not in getFollowers_ids(self.api):
                DIFF_JST_FROM_UTC = 9
                now = datetime.utcnow() + timedelta(hours=DIFF_JST_FROM_UTC)
                time_str = now.strftime('%Y/%m/%d %H:%M:%S')
                self.api.update_status(status="このBotをフォローすると使えます！"+"\n"+"#イ反社にカツ"+"\n"+time_str,in_reply_to_status_id=status.id)
            elif record.created_at.minute != aimed_minute:
                rank = "フライング"
            else:
                rank_list = [s for s in self.status_list if s.created_at.minute == aimed_minute]
                rank = "{rank}位/{total}人".format(
                    rank=str(rank_list.index(record) + 1), total=len(rank_list)
                )
            tweet_text = (
                "@{screen_name} {name}\n".format(
                    screen_name=status.author.screen_name, name=status.author.name
                )
                + "記録: {time}\n".format(
                    time=record.created_at.strftime("%H:%M:%S.%f")[:-3]
                )
                + "順位: {rank}\n".format(rank=rank)
                + "使用クライアント: {client}".format(client=record.source)
            )
            self.api.update_status(tweet_text[:140], in_reply_to_status_id=status.id)
        except:
            self.api.update_status(
                "@{screen_name} 該当データがありませんでした。".format(
                    screen_name=status.author.screen_name
                ),
                in_reply_to_status_id=status.id,
            )
        return True



class Ranker:
    def __init__(self):
        #地域設定
        locale.setlocale(locale.LC_ALL, '')
        #API取得
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        self.api = tweepy.API(auth)
        #その他の設定
        self.screen_name = self.api.verify_credentials()._json["screen_name"]
        self.font_path = path.normpath(FONT_PATH)
        self.img_path = path.normpath(IMG_PATH)
        self.img = Image.new('RGB', (880, 2048), (65,105,225))
        self.user_rank = 0
        #アジアで日にちをとっているから+ timedelta(days=1)いらない．日をまたぐ場合はいるのか
        # self.day = datetime.now(pytz.timezone("Asia/Tokyo")).date() + timedelta(days=1)
        self.day = datetime.now(pytz.timezone("Asia/Tokyo")).date() 
        # title = self.day.strftime("20%y年%m月%d日のランカー集計結果(@{screen_name})".format(screen_name=self.screen_name)).decode('UTF-8')
        title = self.day.strftime(
            "20%y.%m.%dのイ反社にカツ！集計結果(@{screen_name})".format(screen_name=self.screen_name)
        )
        self.draw_text((44, 17), 30, title)

    def draw_text(self, xy, size, text):
        font = ImageFont.truetype(self.font_path, size)
        ImageDraw.Draw(self.img).text(xy, text, font=font, fill='#fff')

    def draw_status(self, status, rank):
        self.draw_text((18, 55 + self.user_rank * 26), 20, rank)
        self.img.paste(Image.open(BytesIO(GET(status.user.profile_image_url_https).content)).resize((26, 26)),(52, 52 + self.user_rank * 26))
        self.draw_text((78, 55 + self.user_rank * 26), 20, status.user.name)
        print(status.user.name)
        #ここの処理ちょっとよくわからん
        self.draw_text((540, 59 + self.user_rank * 26), 13, status.created_at.strftime('%H:%M:%S.') + "%03d" % round(datetime.fromtimestamp(((status.id >> 22) + 1288834974657) / 1000.0).microsecond / 1000))
        self.draw_text((633, 59 + self.user_rank * 26), 13, 'via ' + status.source)
        self.user_rank += 1

    def make_img(self):
        #現在時刻から１日前
        #日本時間を撮っているのになぜか9時間の時差があるので修正する
        #違った．.date()をつけていたため，時刻の切り捨てが生じていた
        since_date = (
            datetime.now(pytz.timezone("Asia/Tokyo")) - timedelta(days=1)
        ).date()
        # print(since_date.date)()
        # self.status_list = [s for s in self.api.list_timeline(u"siroiro_wst", u"しゃろほーの民", count=200) if s.text == u"しゃろほー"]
        self.status_list = [
            s
            for s in tweepy.Cursor(
                self.api.search_tweets,
                #現在時刻
                #ここのuntilを２日後までいれているのは，たぶん１日後だと切り捨てになっている気がするから
                q=f"イ反社にカツ！ since:{since_date} until:{since_date + timedelta(days=2)}",
            ).items(200)
            if s.text == "イ反社にカツ！"
        ]
        # print(self.status_list)
        # print(since_date+timedelta(days=2))
        # for s in tweepy.Cursor(
        #         self.api.search_tweets,
        #         #現在時刻
        #         q=f"イ反社にカツ！ since:{since_date} until:{since_date + timedelta(days=1)}",
        #     ).items(200):
        #     print(s.user.screen_name)
        #     print(s.created_at)
        #フォローしている人だけに限定
        self.status_list = [x for x in self.status_list if x.user.id in getFollowers_ids(self.api)]
        # print(self.status_list)
        # 元の created_at は秒単位の精度しかないので id からミリ秒精度の時刻を付け直す
        for status in self.status_list:
            # status.created_at = self.id_to_datetime(status.id) + timedelta(hours=9)
            # print(status.created_at)
            # status.created_at = self.id_to_datetime(status.id) + timedelta(hours=9)
            status.created_at = self.id_to_datetime(status.id)
            # print(status.created_at)

        self.status_list = sorted(self.status_list, key=lambda x: x.created_at)
        # for status in self.status_list:
        #     print(status.created_at)
        #0:00の人だけを集める
        rank_list = [
            s
            for s in self.status_list
            if s.created_at.minute == aimed_minute and s.created_at.hour == aimed_hour
        ]
        print(rank_list)
        #23:59の人だけを集める
        dq_list = [
            s
            for s in self.status_list
            if s.created_at.minute == aimed_minute - 1 and s.created_at.hour == aimed_hour
        ]
        # print(dq_list)
        #１位の人だけを集める
        winner_list = [s for s in rank_list if s.created_at == rank_list[0].created_at]
        #もしフライングした人がいたら，フライングした人の中で一番0:00に近い人をrank_listの銭湯に加える
        if len(dq_list):
            rank_list.insert(0, dq_list[-1])
        #鍵垢じゃなければ，winnerをRTする
        tmp = "https://twitter.com/ihansyanikatsu/status/"
        self.day = datetime.now(pytz.timezone("Asia/Tokyo")).date() 
        title = self.day.strftime(
            "🔥20%y.%m.%dのイ反社にカツ！の優勝者🔥"
        )
        comment = "おめでとう🎉賞金です！"
        to_tipjpyc = "@tipjpyc tip "
        for winner in winner_list:
            # print(winner.user.name)
            if not winner.user.protected:
                # self.api.retweet(winner.id)
                # self.api.update_status(status = title + "\n" + to_tipjpyc +"@"+winner.user.screen_name + " "+ prize + " " + comment + "\n" + tmp + str(winner.id))
                print(to_tipjpyc +"@"+winner.user.screen_name + " "+ prize + " " + title + "\n" + tmp + str(winner.id))
                # print(winner.user.screen_name)
        #描画処理を行う
        # print(len(dq_list))
        if len(dq_list):
            self.draw_status(rank_list[0], "DQ.")
            for i in range(1, min(len(rank_list), 76)):
                self.draw_status(rank_list[i], str(i))
        else:
            # print(min(len(rank_list), 76))
            for i in range(1, min(len(rank_list), 76)):
                print(i)
                self.draw_status(rank_list[i - 1], str(i))
        #作った画像を切り取る
        box = (0, 0, 880, 59 + (self.user_rank + 3) * 26)
        self.img = self.img.crop(box)
        self.img.show()
        #画像を保存
        self.img.save(self.img_path, "JPEG", quality=100, optimize=True)


    #timeout処理．600秒経ったらタイムアウトする
    @timeout(60 * 10)
    def reply_to_mention(self):
        # listener = Listener(self.status_list, self.api)
        # stream = tweepy.Stream(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET, listener)
        # stream.filter(track=["@" + self.screen_name])
        # stream = tweepy.Stream(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET)
        listener = Listener(CONSUMER_KEY,CONSUMER_SECRET,ACCESS_TOKEN,ACCESS_TOKEN_SECRET,self.status_list, self.api)
        listener.filter(track=["@" + self.screen_name])

    @staticmethod
    def id_to_datetime(status_id):
        return datetime.fromtimestamp(((status_id >> 22) + 1288834974657) / 1000.0)

def main(data, context):
    #インスタンス作成
    bot = Ranker()
    DIFF_JST_FROM_UTC = 9
    now = datetime.utcnow() + timedelta(hours=DIFF_JST_FROM_UTC)
    time_str = now.strftime('%Y/%m/%d %H:%M:%S')
    #観測開始をツイート
    # bot.api.update_status("イ反社にカツ！を観測中"+time_str)
    bot.api.update_status("テスト中です〜"+time_str)
    #2分まつ
    # sleep(120)
    #ランキング画像を作成s
    bot.make_img()
    #画像をツイート
    now = datetime.utcnow() + timedelta(hours=DIFF_JST_FROM_UTC)
    time_str = now.strftime('%H:%M:%S')
    bot.api.update_status_with_media(
        filename=bot.img_path, status=bot.day.strftime("20%y.%m.%dのイ反社にカツ！の集計結果"+ "\n" +time_str)
    )
    IMG_PATH.unlink(missing_ok=True)
    try:
        # Listenerを起動してメンションを検知している
        print("try実行")
        bot.reply_to_mention()
    except:
        print("except実行")
        sys.exit()
    # bot.reply_to_mention()


# if __name__ == "__main__":
#     main()


# ranker = Ranker()
# print(ranker.screen_name)

