import requests
import json
import string
import unicodedata
from glob import glob
from os import getcwd, makedirs, remove
from os.path import join, basename, exists
from shutil import move
from random import randint
from mutagen.easyid3 import EasyID3
from mutagen import File
from mutagen.mp3 import MP3, HeaderNotFoundError
from mutagen.id3 import ID3, APIC, error, ID3NoHeaderError
import mimetypes

FORCE_ALL = False

validFilenameChars = "-_.() %s%s" % (string.ascii_letters, string.digits)
def removeDisallowedFilenameChars(filename):
    cleanedFilename = unicodedata.normalize('NFKD', filename).encode('ASCII', 'ignore')
    return ''.join(c for c in cleanedFilename if c in validFilenameChars)


class Hyped:
    def __init__(self):
        pass
    
    #__INIT__ passes in the username and password then tries to authenticate with HypeM
    def __init__(self, usernm, passwrd):
        self.hype_user = usernm
        self.hype_pass = passwrd
        self.hype_authenticate()
        self.hype_path = getcwd()
        self.hype_fav_path = join(getcwd(),self.favorite_folder)
        self.hype_duplicate_path = join(getcwd(),self.duplicate_folder)
        self.hype_missing_path = join(getcwd(),self.missing_folder)
        self.hype_unsorted_path = join(getcwd(),self.unsorted_folder)
        
        if not exists(self.hype_fav_path):
            makedirs(self.hype_fav_path)
        if not exists(self.hype_duplicate_path):
            makedirs(self.hype_duplicate_path)
        if not exists(self.hype_missing_path):
            makedirs(self.hype_missing_path)
        if not exists(self.hype_unsorted_path):
            makedirs(self.hype_unsorted_path)
        return
    
    # HYPE_AUTHENTICATE authenticates with the HypeM api and sets the user token.
    def hype_authenticate(self):
        data = {
            u'username':self.hype_user,
            u'password':self.hype_pass,
            u'device_id':self.device_id
        }
        
        hype_auth_result = requests.post(self.authurl,data=data,headers=self.auth_headers)
        self.hype_token = hype_auth_result.json()['hm_token']
        self.hype_cookie = hype_auth_result.cookies
        status = hype_auth_result.json()['status']
        return status

    #GET_PROFILE gets the profile data from the Hypem api and sets the amount of favorites
    def get_profile(self):
        headers = {
            'User-Agent': 'Plug for OSX/0.10.4',
            'Content-Type': 'application/json'
        }
        
        url = self.profile_url.format(self.hype_user)
        
        profile = requests.get(url,headers=headers,cookies=self.hype_cookie)
        self.hype_user_profile = profile.json()
        self.hype_user_favorites_count = self.hype_user_profile['favorites_count']['item']
        return

    def get_user_profile(self,username):
        headers = {
            'User-Agent': 'Plug for OSX/0.10.4',
            'Content-Type': 'application/json'
        }
        
        url = self.profile_url.format(username)
        
        profile = requests.get(url,headers=headers,cookies=self.hype_cookie)
        return profile.json()

    #GET_FAVORITES gets the list of user favorites based on page and count
    def get_favorites(self,page,count):
        #count = 2000
        token = self.hype_token
        url = self.hype_fav_url.format(page,count,token)
        headers = self.api_headers
        cookie = self.hype_cookie
        favorite_list = requests.get(url,headers=headers,cookies=cookie)
        return favorite_list.json()
    
    def get_user_favorites(self,username,page,count):
        #count = 2000
        token = self.hype_token
        url = self.hype_user_fav_url.format(username,page,count,token)
        headers = self.api_headers
        cookie = self.hype_cookie
        favorite_list = requests.get(url,headers=headers,cookies=cookie)
        return favorite_list.json()
    
    def get_popular(self):
        return


    #GET_NUM_FAVORITES gets the number of favorites
    def get_num_favorites(self):
        if(self.hype_user_favorites_count == None):
            self.get_profile()
        return self.hype_user_favorites_count
    

    #GET_NUM_PAGES calculates the number of pages
    def get_num_pages(self):
        if(self.hype_user_favorites_count == None):
            self.get_profile()
        numFavs = self.hype_user_favorites_count
        if numFavs % 40:
            return int(numFavs /40) + 1
        else:
            return int(numFavs /40)

    def get_json(self):
        url = self.ssl_url + "/v2/me/favorites?hm_token={}".format(self.hype_token)
        headers = self.api_headers
        cookie = self.hype_cookie
        favorite_list = requests.get(url,headers=headers,cookies=cookie)
        return favorite_list.json()

    def get_tracklist(self,playlist,is_shuffled):
        options = {
            'popular' : self.playlist_popular,
            'popular_noremix' : self.playlist_popular_noremix,
            'favorites' : self.playlist_favorites
        }
        list = options[playlist]()
        if(is_shuffled):
            list = self.shuffle_list(list)
        return list

    # part of the dictionary "switch" listed in get_tracklist
    def playlist_popular(self):
        token = self.hype_token
        headers = self.api_headers
        cookie = self.hype_cookie
        url = self.ssl_url + "/v2/popular?mode=now&page={}&count={}&hm_token={}".format(1,50,token)
        list = requests.get(url,headers=headers,cookies=cookie)
        return list.json()

    # part of the dictionary "switch" listed in get_tracklist
    def playlist_popular_noremix(self):
        token = self.hype_token
        headers = self.api_headers
        cookie = self.hype_cookie
        url = self.ssl_url + "/v2/popular?mode=noremix&page={}&count={}&hm_token={}".format(1,50,token)
        list = requests.get(url,headers=headers,cookies=cookie)
        return list.json()

    # part of the dictionary "switch" listed in get_tracklist
    def playlist_favorites(self):
        token = self.hype_token
        headers = self.api_headers
        cookie = self.hype_cookie
        url = self.ssl_url + "/v2/me/favorites?page={}&count={}&hm_token={}".format(1,40,token)
        list = requests.get(url,headers=headers,cookies=cookie)
        return list.json()

    # shuffles a playlist json of variable size
    def shuffle_list(self,list):
        newlist = []
        while (len(list)):
            i = randint(0, (len(list)-1))
            newlist.append(list[i])
            list.pop(i)
        return newlist

    #STREAM_URLS converts a playlist into urls that can be loaded into a media player/streamer
    def stream_urls(self, playlist, is_shuffled):
        list = self.get_tracklist(playlist,is_shuffled)
        key = self.hype_public_key
        stream_url_list = []
        for i in xrange(len(list)):
            id = list[i]['itemid']
            url = self.media_url.format(id,key)
            stream_url_list.append({'stream_url':url})
        return stream_url_list
    
    def download_me_fav(self):
        print "DOWNLOADING FAVORITES"
        num = self.hype_user_favorites_count
        tracks = list(reversed(self.get_favorites(1,num)))
        self.json_tracks = tracks
        self.download_tracklist(tracks,self.favorite_folder)
    
    #newlist = oldlist[::-1] fasted way to reverse
    def download_user_fav(self,username):
        print "DOWNLOADING {} FAVORITES".format(username)
        profile = self.get_user_profile(username)
        fav_count = profile['favorites_count']['item']
        listed = self.get_user_favorites(username,1,fav_count)
        tracks = list(reversed(listed))
        self.json_tracks = tracks
        self.download_tracklist(tracks,self.favorite_folder)
    #got it to head the mp3 and the thumb. need to check if already there
    #and to do the id3 tags
    def download_tracklist(self,tracks,folder):
        key = self.hype_public_key
        songs_in_folder = []
        track_num = 1
    
        for track in tracks:
            id = track[u"itemid"]
            artist = removeDisallowedFilenameChars(track[u"artist"])
            title = removeDisallowedFilenameChars(track[u"title"])
            audio_url = self.media_url.format(id,key)
            thumb_url = track[u"thumb_url_large"]
            filename_title = "{} - {} - {}".format(track_num, artist, title)
            track_title = "{} - {}".format(artist, title)
            audio_filename = ''
            thumb_filename = ''
            file_path = ''
            
            print filename_title
            in_folder, file_path = self.organize(track_num,track_title,folder)
            
            if in_folder == True:
                if file_path != '':
                    self.write_tags(track_num,track,file_path)
                songs_in_folder.append(filename_title)
                track_num += 1
                continue
            else:
                in_missing, file_path = self.check_missing_folder(track_num,track_title)
                if in_missing == True:
                    self.write_tags(track_num,track,file_path)
                    songs_in_folder.append(filename_title)
                    track_num += 1
                    continue
                try:
                    audio_filename, file_path = self.download_file(audio_url,filename_title,folder)
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code
                    if status_code == 404:
                        self.add_missing_track(track)
                        status = "\t{} {}".format("Not Found",filename_title)
                        print status
                        track_num += 1
                        continue
                except requests.exceptions.ConnectionError as e:
                    print e
                    print "\tDang maybe next time..."
                    self.add_missing_track(track)
                    track_num += 1
                    continue
    

            if file_path != '':
                self.write_tags(track_num,track,file_path)
            songs_in_folder.append(filename_title)
            track_num += 1
        self.filter_folder(songs_in_folder,folder)
        self.write_missing_json()

    def check_all_fav(self):
        tracks = reversed(fav_json)
        track_num = 1
        songs_in_folder = []
        missing_tracks = []
        for track in tracks:
            id = track[u"itemid"]
            artist = removeDisallowedFilenameChars(track[u"artist"])
            title = removeDisallowedFilenameChars(track[u"title"])
            filename_title = "{} - {} - {}".format(track_num, artist, title)
            file_title = "{} - {}".format(artist, title)
            
            in_folder, file_path = self.organize(track_num,file_title)
            
            if in_folder == False:
                in_missing, file_path = self.check_missing_folder(track_num,file_title)
                if in_missing == False:
                    missing_tracks.append(filename_title)
                    print filename_title

            if file_path != '':
                self.write_tags(track_num,track,file_path)
            
            songs_in_folder.append(filename_title)
            track_num += 1
        #print songs_in_folder
        self.filter_fav_folder(songs_in_folder)
        print missing_tracks


    def get_extention(self,headers):
        ext = ''
        if headers['Content-Type'] == 'audio/mpeg':
            ext = '.mp3'
        elif headers['Content-Type'] == 'audio/mp3':
            ext = '.mp3'
        elif headers['Content-Type'] == 'image/jpeg':
            ext = '.jpg'
        elif headers['Content-Type'] == 'image/png':
            ext = '.png'
        elif headers['Content-Type'] == 'image/tiff':
            ext = '.tiff'
        elif headers['Content-Type'] == 'audio/x-wav':
            ext = '.wav'
        elif headers['Content-Type'] == 'audio/x-aac':
            ext = '.aac'
        elif headers['Content-Type'] == 'audio/mp4':
            ext = '.mp4a'
        elif headers['Content-Type'] == 'audio/mp3; charset=UTF-8':
            ext = '.mp3'
        elif headers['Content-Type'] == 'application/octet-stream':
            ext = '.mp3'
        else:
            ext = headers['Content-Type']
        return ext

    def download_file(self,url,filename,folder_path):
        full_filename = ''
        r = requests.get(url,stream=True,headers=self.api_headers,timeout=30)
        if r.status_code == 200:
            full_filename = filename + self.get_extention(r.headers)
            full_write_path = join(folder_path,full_filename)
            with open(full_write_path, 'wb') as f:
                for byte in r.iter_content(1024):
                    f.write(byte)
        else:
            r.raise_for_status()
        return full_filename, full_write_path

    def download_thumb(self,url,filename):
        full_filename = ''
        r = requests.get(url,stream=True,headers=self.api_headers)
        if r.status_code == 200:
            full_filename = filename + self.get_extention(r.headers)
            full_write_path = join(self.hype_unsorted_path,full_filename)
            with open(full_write_path, 'wb') as f:
                for byte in r.iter_content(1024):
                    f.write(byte)
        else:
            r.raise_for_status()
        return full_filename, full_write_path


    def get_file_head(self,url,filename):
        full_filename = ''
        r = requests.head(url,stream=True,headers=self.api_headers,
                          allow_redirects=True)
        if r.status_code == 200:
            ext = self.get_extention(r.headers)
            full_filename = filename + ext
            print ext
        else:
            r.raise_for_status()
        return full_filename

    def track_title_list(self):
        a_list = []
        track_num = 1
        track_list = self.json_tracks
        for track in track_list:
            id = track[u"itemid"]
            artist = removeDisallowedFilenameChars(track[u"artist"])
            title = removeDisallowedFilenameChars(track[u"title"])
            filename_title = "{} - {} - {}".format(track_num, artist, title)
            a_list.append(filename_title)
            track_num += 1
        return a_list

    def move_duplicate(self,dup_list):
        for i in dup_list:
            source = i
            destination = join(self.hype_duplicate_path,basename(source))
            try:
                move(source, destination)
            except IOError as e:
                if e.errno == 2:
                    makedirs(self.hype_duplicate_path)
                    move(source, destination)

    def move_unsorted(self,file_list):
        for i in file_list:
            source = i
            destination = join(self.hype_unsorted_path,basename(source))
            try:
                move(source, destination)
            except IOError as e:
                if e.errno == 2:
                    makedirs(self.hype_unsorted_path)
                    move(source, destination)

    #to call find(l, lambda x: 'something' in x)
    def find_first(self,lst, predicate):
        return next((i for i,j in enumerate(lst) if predicate(j)), -1)


    def organize(self,track_num,title,folder_path):
        file_title = "{} - {}".format(track_num,title)
        duplicates = glob(join(folder_path,'*' + file_title + '*'))
        same_title = glob(join(folder_path,'*' + title + '*'))
        list_size = len(duplicates)
        file_path = ''
        filtered_same_title = []
        compare_list = self.track_title_list()
        for track in same_title:
            if basename(track)[:-4] in compare_list:
                continue
            filtered_same_title.append(track)

        if (len(filtered_same_title) == 0) and (len(duplicates) == 0):
            return False, ''
        elif (len(filtered_same_title) == 0) and (len(duplicates) == 1):
            return True, ''
        elif (len(duplicates) > 0) or (len(filtered_same_title) > 0):
            mergedlist = list(set(duplicates + filtered_same_title))
            new_list = []
            if "remix" not in title.lower():
                for file in mergedlist:
                    if "remix" in basename(file).lower():
                        continue
                    new_list.append(file)
            list_pos = self.find_first(new_list, lambda x: title in x)
            if list_pos == -1:
                self.move_duplicate(new_list)
                return False, ''
            source = new_list.pop(list_pos)
            file_type = basename(source).split('.')[-1]
            filename = file_title + '.' + file_type
            destination = join(folder_path,filename)
            move(source,destination)
            self.move_duplicate(new_list)
            return True, destination
        else:
            return False, ''

    def filter_folder(self,fav_file_list,folder_path):
        print "FILTERING FAVORITES"
        new_list = []
        file_list = glob(join(folder_path,'*'))
        for file in file_list:
            if basename(file)[:-4] in fav_file_list:
                continue
            new_list.append(file)
        self.move_unsorted(new_list)

    def check_missing_folder(self,track_num,title):
        file_title = "{} - {}".format(track_num,title)
        matched_missing = glob(join(self.hype_missing_path,'*' + title + '*'))
        track_list = self.track_title_list()
        new_list = []
        if len(matched_missing) > 0:
            if "remix" not in file_title.lower():
                for track in matched_missing:
                    if "remix" in basename(track).lower():
                        continue
                    new_list.append(track)
                matched_missing = new_list
            if len(matched_missing) == 0:
                return False, ''
            source = matched_missing[0]
            file_type = basename(source).split('.')[-1]
            filename = file_title + '.' + file_type
            destination = join(self.hype_fav_path,filename)
            move(source,destination)
            return True, destination
        else:
            return False, ''

    def add_missing_track(self,track):
        id = track[u"itemid"]
        artist = removeDisallowedFilenameChars(track[u"artist"])
        title = removeDisallowedFilenameChars(track[u"title"])
        filename = "{} - {}".format(artist,title)
        thumb_url = track[u"thumb_url_large"]
        self.missing_tracks.append({u"itemid":track[u"itemid"],
                                    u"artist":track[u"artist"],
                                     u"title":track[u"title"],
                            u"thumb_url_large":track[u"thumb_url_large"],
                                  u"filename":filename
                                   })
    def write_missing_json(self):
        with open(join(self.hype_missing_path,'missing.json'),'w') as f:
            json.dump(self.missing_tracks, f, sort_keys = True, indent = 4)

    def write_tags(self,track_num,track,path):
        id = track[u"itemid"]
        artist = removeDisallowedFilenameChars(track[u"artist"])
        title = removeDisallowedFilenameChars(track[u"title"])
        unicode_artist = track[u"artist"]
        unicode_title = track[u"title"]
        thumb_url = track[u"thumb_url_large"]
        file_title = "{} - {} - {}".format(track_num, artist, title)
        audio_file_path = path
        z , thumb_path = self.download_thumb(thumb_url,file_title)
        
        try:
            audio = ID3(audio_file_path)
            audio.delete()
        except ID3NoHeaderError, e:
            pass
            #audio = MP3(audio_file_path)
            #except HeaderNotFoundError, e:
            #print file_title
        meta = File(audio_file_path, easy=True)
        try:
            meta.add_tags()
        except AttributeError as e:
            print e
            print audio_file_path
            remove(thumb_path)
            return
        except error as e:
            if e.message == "an ID3 tag already exists":
                pass
            else:
                raise e
        meta['artist'] = unicode_artist
        meta['title'] = unicode_title
        meta['tracknumber'] = str(track_num)
        meta.save()

        audio = ID3(audio_file_path)
        audio.add(
                  APIC(
                       encoding = 3, # 3 is for utf-8
                       mime = mimetypes.guess_type(thumb_path)[0],
                       type = 3,
                       desc = u'Cover',
                       data = open(thumb_path).read()
                       )
                  )
        audio.save()
        remove(thumb_path)
        return



    hype_user = None
    hype_pass = None
    hype_token = None
    hype_cookie = None
    hype_user_profile = None
    hype_user_favorites_count = None
    device_id = ''
    hype_public_key = '' #must provide your own
    ssl_url = "https://api.hypem.com"
    api_url = "https://api.hypem.com/v2/"
    authurl = "https://api.hypem.com/v2/get_token"

    media_url = "https://hypem.com/serve/public/{}?key={}"
    
    profile_url = 'https://api.hypem.com/api/get_profile?username={}' #.format(hype_user)
    hype_fav_url =  api_url + "me/favorites?page={}&count={}&hm_token={}" #.format(page,count,self.hm_token)
    hype_user_fav_url = api_url + "users/{}/favorites?page={}&count={}&hm_token={}"
    
    auth_headers = {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Content-Transfer-Encoding': '8bit',
    'User-Agent': 'Plug for OSX/0.10.4',
    }
    
    api_headers = {
    'User-Agent': 'Plug for OSX/0.10.4',
    }
    
    auth_data = {u'username':hype_user,u'password':hype_pass,u'device_id':device_id}
    favorite_folder = 'Favorites'
    duplicate_folder = 'Duplicates'
    missing_folder = 'Missing'
    unsorted_folder = 'Unsorted'
    hype_path = None
    hype_fav_path = None
    hype_duplicate_path = None
    hype_missing_path = None
    hype_unsorted_path = None
    json_tracks = []
    missing_tracks =  []
def main():
    scrape = Hyped('USERNAME','PASS') #replace with hypem username and pass
    scrape.get_profile()
    scrape.download_me_fav()


if __name__ == "__main__":
    main()

