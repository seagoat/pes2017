# -*- coding: utf8 -*-

import urllib.request
from urllib.request import urlretrieve
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse, urlencode, urlunparse, parse_qsl
from urllib.parse import parse_qs
import os.path
from time import sleep
import pandas as pd
import gc


LOCAL_PLAYER_PATH = './localdb/'


def getPageList(url_home):
    # get all sub page's url form special url
    page_url_list = [url_home, ]

    response = urllib.request.urlopen(url_home)
    html_home = response.read()

    soup_home = BeautifulSoup(html_home, "lxml")

    # get page number, get player number

    page_list = soup_home.find_all('div', attrs={"class": "pages"})

    max_page_num = -1

    for page in page_list:
        # print(page)
        for page_a in page.find_all(href=re.compile('page=')):
            href = page_a['href']
            page_num_pos = href.rfind('=')
            page_num = int(href[page_num_pos+1:])
            if page_num > max_page_num:
                max_page_num = page_num
            # next_url = urljoin(url_home, page_a['href'])
            # print(next_url)
            # page_url_list.append(next_url)

    print(max_page_num)

    parse_result = urlparse(url_home)
    url_parts = list(parse_result)
    print(parse_result.query)
    query = dict(parse_qsl(parse_result.query))

    for page_num in range(0, max_page_num + 1, 1):
        # print(page_num)
        query.update({'page': page_num})
        url_parts[4] = urlencode(query)
        page_url = urlunparse(url_parts)

        page_url_list.append(page_url)
    return page_url_list


def getPlayerList(player_list_url):
    # get all sub page's url form special url
    player_url_list = []

    response = urllib.request.urlopen(player_list_url)
    player_list_html = response.read()

    soup_player_list = BeautifulSoup(player_list_html, "lxml")

    # get page number, get player number

    player_table_list = soup_player_list.find_all('table',
                                                  attrs={"class": "players"}
                                                  )
    for player_table in player_table_list:
            # print(player_table)
            for player in player_table.find_all(href=re.compile('id=')):
                # print(player['href'])
                next_url = urljoin(player_list_url, player['href'])
                # print(next_url)
                player_url_list.append(next_url)

    return player_url_list


def getPlayerID(url):
    parse_result = urlparse(url)
    id = parse_result.query.split('=')[1]
    return id


def retry(attempt):
    def decorator(func):
        def wrapper(*args, **kw):
            att = 0
            while att < attempt:
                try:
                    func(*args, **kw)
                    return

                except Exception as e:
                    print('Failed')
                    sleep(120)
                    att += 1
        return wrapper
    return decorator


@retry(attempt=5)
def downloadPlayerPage(url):
    id = getPlayerID(url)
    print('downloading player[{}]'.format(id))

    opener = urllib.request.build_opener()
    opener.addheaders = [('X-Forwarded-For', '8.8.8.8')]

    urllib.request.install_opener(opener)

    response = urlretrieve(url, './localdb/{}.html'.format(id))
    sleep(4)


def getLastPage():
    try:
        with open('./localdb/lastpage', 'r') as f:

            last_page = int(f.readline())
            print('Read Last Page [{}] from lastpage file'.format(last_page))
            return last_page
        f.close()

    except Exception as e:
        print(e)
        return 0


def writeLastPage(last_page):

    try:
        with open('./localdb/lastpage', 'w') as f:
            f.write(str(last_page))
            print('Write last page[{}] succeeded'.format(last_page))
        f.close()

    except Exception as e:
        print(e)
        return


def downloadAllPlayers(url_home):
    # check downloaded file
    file_path = LOCAL_PLAYER_PATH

    downloaded_filelist = []

    for root, dirs, files in os.walk(file_path):
        for name in files:
            downloaded_filelist.append(name)

    downloaded_count = len(downloaded_filelist)

    page_count = 0
    player_count = 0
    last_page = getLastPage()
    print('Will recovery from Page[{}]'.format(last_page))

    page_list = getPageList(url_home)

    for page in page_list[last_page:]:
        print('PAGE [{}] Parsing page {}'.format(page_count + last_page, page))

        player_list = getPlayerList(page)
        # print(player_list)

        for player in player_list:
            id = getPlayerID(player)
            filename = '{}.html'.format(id)
            if filename in downloaded_filelist:
                print('PLAYER [{}/{}] [id = {}] skipped'.format(
                                        player_count, downloaded_count, id))
                continue

            downloadPlayerPage(player)

            player_count += 1
            print('PLAYER [{}/{}] [id = {}] downloaded'.format(
                                        player_count, downloaded_count, id))

        page_count += 1
        writeLastPage(last_page+page_count)

    print('Done!!! totla {} players have been downloaded'.format(count))


def createLocalDB():
    file_path = LOCAL_PLAYER_PATH

    scout_local_db = []

    player_index = 0
    for dirpath, dirnames, filenames in os.walk(file_path):
        for name in filenames[6999:]:
            if not name.endswith('.html'):
                continue
            full_filename = os.path.join(dirpath, name)
            # print(full_filename)

            player_id = name.split('.')[0]

            # if player_id != '34098':
            #     continue

            scout_for_1player = []

            # print(full_filename)
            with open(full_filename) as file:
                soup = BeautifulSoup(file, 'lxml')

                # print(soup.prettify())
                player_name = soup.title.string[:-1*len(' - pesdb.net')]
                # print(player_name)
                overall_rating = soup.find_all(id='a23')[0].string
                position_tag = soup.find_all('th', text='Position:')

                for sibling in position_tag[0].next_siblings:
                    position = sibling.string
                    break
                else:
                    position = 'Unknown'
                    print('Unknow postion for play [{}]{}'.format(player_id,
                                                                  player_name))

                print('[{}] {} {} {} {}'.format(player_index,
                                                player_id,
                                                player_name,
                                                overall_rating,
                                                position))
                player_index += 1
                # find all scout combine
                scout_combine_list = soup.find_all('tr', class_='scout_row')
                for scout_combine in scout_combine_list:
                    # print(scout_combine)
                    data_free = scout_combine['data-free']
                    data_percent = scout_combine['data-percent']
                    # print(scout_combine)
                    href = scout_combine.td.a['href']
                    # star = scout_combine.td.a.string

                    one_scout = {
                        'id': player_id,
                        'name': player_name,
                        'rating': int(overall_rating),
                        'position': position,
                        'free': int(data_free),
                        'percent': int(data_percent),
                        # 'href': href
                        # 'scout1: '',
                        'id1': '',
                        # 'scout2': '',
                        'id2': '',
                        # 'scout3': '',
                        'id3': '',
                        # 'scout-id-list': []
                    }

                    result = parse_qs(href[3:])

                    scout_index = 0
                    for key, value in sorted(result.items(),
                                             key=lambda d: d[0]):

                        # print(key, value)
                        if key == 'scout_stars':
                            # one_scout['star'] = value[0]
                            continue

                        if scout_index > 3:
                            print('Error!!, too many scouts. Break')
                            break

                        scout_index += 1
                        # one_scout['scout{}'.format(scout_index)] = key
                        one_scout['id{}'.format(scout_index)] = int(value[0])
                        # one_scout['scout-id-list'].append(value[0])

                    # print(one_scout)
                    if one_scout in scout_for_1player:
                        # filter dirrent star value scout
                        continue

                    scout_for_1player.append(one_scout)

                print(len(scout_for_1player))
                scout_local_db.extend(scout_for_1player)
                # only do once for unit test
                # break

                soup.decompose()

                if player_index % 1000 == 0:
                    gc.collect()
                    print(player_index)
                    df = pd.DataFrame(scout_local_db)
                    df.to_excel('pes2017_localdb_{}.xlsx'.format(player_index))
                    print('pesdb 2017 local database file exported')
                    scout_local_db = []
                    pass

    print(len(scout_local_db))
    df = pd.DataFrame(scout_local_db)
    df.to_excel('pes2017_localdb_{}.xlsx'.format(player_index))
    print('pesdb 2017 local database file exported')


if __name__ == '__main__':
    # test create local db
    if 1:
        createLocalDB()

    # test get last page
    if 0:
        writeLastPage(0)
        print(getLastPage())

    if 0:

        # test code
        # all players
        url_home = 'http://pesdb.net/pes2017/'
        downloadAllPlayers(url_home)

    if 0:
        sample_url = 'http://pesdb.net/pes2017/?id=5770'
        downloadPlayerPage(sample_url)

    if 0:

        sample_url = 'http://pesdb.net/pes2017/?scout_percent=100&page=37'
        for player in getPlayerList(sample_url):
            print(player)

        # test code
        # all 100% percent player
        url_home = 'http://pesdb.net/pes2017/'
        url_list = getPageList(url_home)
        for url in url_list:
            print(url)

        url_home = 'http://pesdb.net/pes2017/?scout_percent=100'
        url_list = getPageList(url_home)
        for url in url_list:
            print(url)
