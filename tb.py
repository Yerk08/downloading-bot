import telebot
from pickle import dump, load
import os
from threading import Thread
from requests import get, post
from random import randint as rand
from qbittorrent import Client as qClient
from time import sleep
from subprocess import PIPE, Popen

token = "<your code>"

timeupd = 600
useupd = True
adminpass = "<your password>"

MAXSIZE = 2000 * 1024 * 1024 - 16384
MAXMESSAGESIZE = 4096
torrentIP = "http://localhost:8080"

bot = telebot.TeleBot(token, num_threads = 30)

def get_size_format(b, factor=1024, suffix="B"):
    """
    Scale bytes to its proper byte format
    e.g:
        1253656 => '1.20MB'
        1253656678 => '1.17GB'
    """
    for unit in ["", "K", "M", "G", "T", "P", "E", "Z"]:
        if b < factor:
            return f"{b:.2f}{unit}{suffix}"
        b /= factor
    return f"{b:.2f}Y{suffix}"


def init():
    global DATA, qbittorrentclient, minecraftconread, minecraftconwrite
    if os.path.exists("/telegram_bots/datafile.dat"):
        DATA = load(open("/telegram_bots/datafile.dat", 'rb'))
    else:
        DATA = dict()
    def autosave():
        while True:
            sleep(timeupd)
            dump(DATA, open("/telegram_bots/datafile.dat", 'wb'))
    if useupd:
        thr = Thread(target=autosave)
        thr.daemon = True
        thr.start()

    if not "usersNOW" in DATA:
        DATA["usersNOW"] = dict()
    if not "usersLogin" in DATA:
        DATA["usersLogin"] = set()
    if not "admin" in DATA:
        DATA["admin"] = set()
    if not "hasFP" in DATA:
        DATA["hasFP"] = set()
    if not "loginpass" in DATA:
        DATA["loginpass"]=''.join(map(chr,[rand(ord('A'),ord('Z')) for i in range(12)]))
    qbittorrentclient = qClient(torrentIP)
    print("Connect torrent (None - good):", qbittorrentclient.login("admin", adminpass))
    if os.path.exists("/minecraft_servers/1.20.4/world/session.lock"):
        os.remove("/minecraft_servers/1.20.4/world/session.lock") 
    def minecraftstartwrite():
        global minecraftconwrite
        minecraftconwrite = None
        minecraftconwrite = open("/minecraft_servers/1.20.4/pipe_in", 'a')
        print("Minecraft write - ok")
    if not "mineadmins" in DATA:
        DATA["mineadmins"] = set()
    def mineserversender():
        global minecraftconread
        minecraftconread = open("/minecraft_servers/1.20.4/pipe_out", 'r')
        print("Minecraft read - ok")
        messend = ""
        while True:
            try:
                mes = minecraftconread.readline()
            except:
                break
            os.set_blocking(minecraftconread.fileno(), False)
            if not "[STDERR/]" in mes: #Just a lot of errors
                if mes == "" and messend == "":
                    os.set_blocking(minecraftconread.fileno(), True)
                elif len(messend + mes) < MAXMESSAGESIZE and mes != "":
                    messend = messend + mes
                else:
                    try:
                        for admin in DATA["mineadmins"]:
                            try:
                                bot.send_message(admin, messend)
                            except:
                                pass
                        messend = ""
                    except:
                        pass
                    if len(messend + mes) < MAXMESSAGESIZE and mes != "":
                        messend = messend + mes

    # -- Uncomment for minecraft work --
    #thrr = Thread(target = mineserversender)
    #thrr.daemon = True
    #thrr.start()
    #thrw = Thread(target = minecraftstartwrite)
    #thrw.daemon = True
    #thrw.start()



@bot.message_handler()
def start_message(message):
    global DATA
    if not message.chat.id in DATA["usersNOW"]:
        DATA["usersNOW"][message.chat.id]="None"

    if DATA["usersNOW"][message.chat.id]=="None":

        if message.text=="/login":
            if not message.chat.id in DATA["usersLogin"]:
                DATA["usersNOW"][message.chat.id]="write_code"
                bot.send_message(message.chat.id, "Введи код доступа")
            else:
                bot.send_message(message.chat.id, "Вы уже вошли")
        elif message.text=="/logout":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы ещё не вошли")
            else:
                DATA["usersNOW"][message.chat.id]="sure_logout"
                bot.send_message(message.chat.id, "Вы уверены? Если да - то напишите \"да\" маленькими буквами")


        elif message.text=="/admin":
            if not message.chat.id in DATA["admin"]:
                DATA["usersNOW"][message.chat.id]="write_code_admin"
                bot.send_message(message.chat.id, "Введи код доступа")
            else:
                bot.send_message(message.chat.id, """Ваши команды:
/seepass
/blockuser
/blockuserall

/seetorrents
/getfromhash
/pausealltorrents
/resumealltorrents

/deletealltorrents
/permanentdeletealltorrents

/addmetominecraftlistreaders
/removemefromminecraftlistreaders
/sendcommandtominecraft

/commandsendermode

/fullstop""")
        elif message.text=="/seepass":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                bot.send_message(message.chat.id, DATA["loginpass"])
        elif message.text=="/fullstop":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="sure_fullstop"
                bot.send_message(message.chat.id, "Вы уверены? Если да - то напишите \"да\" маленькими буквами")
        elif message.text=="/seetorrents":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                torrents = qbittorrentclient.torrents()
                answer = ""
                for torrent in torrents:
                    answer+="Имя торрента: "+str(torrent["name"])+'\n'
                    answer+="Количество сидов: "+str(torrent["num_seeds"])+'\n'
                    answer+="Хэш: "+str(torrent["hash"])+'\n'
                    answer+="Размер файла: "+get_size_format(torrent["total_size"])+'\n'
                    answer+="Скорость загрузки: "+get_size_format(torrent["dlspeed"]) + "/s\n"
                    answer+='\n'
                if len(answer) == 0:
                    bot.send_message(message.chat.id, "Пока что нет торрентов.")
                else:
                    i=0
                    while i<len(answer):
                        bot.send_message(message.chat.id, answer[i:i+MAXMESSAGESIZE])
                        i += MAXMESSAGESIZE
                        sleep(1)
        elif message.text=="/pausealltorrents":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                bot.send_message(message.chat.id, str(qbittorrentclient.pause_all()))
        elif message.text=="/resumealltorrents":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                bot.send_message(message.chat.id, str(qbittorrentclient.resume_all()))
        elif message.text=="/deletealltorrents":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="sure_deleteall"
                bot.send_message(message.chat.id, "Вы уверены? Если да - то напишите \"да\" маленькими буквами")
        elif message.text=="/permanentdeletealltorrents":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="sure_permanentdeleteall"
                bot.send_message(message.chat.id, "Вы уверены? Если да - то напишите \"да\" маленькими буквами")
        elif message.text=="/getfromhash":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="get_data_from_hashtorrent"
                bot.send_message(message.chat.id, "Введите хеш нужного торрента")
        elif message.text=="/blockuser":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="block_user"
                bot.send_message(message.chat.id, "Введите имя пользователя")
        elif message.text=="/blockuserall":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="sure_block_user_all"
                bot.send_message(message.chat.id, "Вы уверены? Если да - то напишите \"да\" маленькими буквами")
        elif message.text=="/addmetominecraftlistreaders":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                if message.chat.id in DATA["mineadmins"]:
                    bot.send_message(message.chat.id, "Вы уже читаете сообщения сервера Minecraft")
                else:
                    DATA["mineadmins"].add(message.chat.id)
                    bot.send_message(message.chat.id, "Теперь вы читаете сообщения сервера Minecraft")
        elif message.text=="/removemefromminecraftlistreaders":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                if message.chat.id in DATA["mineadmins"]:
                    DATA["mineadmins"].remove(message.chat.id)
                    bot.send_message(message.chat.id, "Функция чтения сообщений сервера Minecraft отключена")
                else:
                    bot.send_message(message.chat.id, "Вы ещё не начали читать сообщения сервера Minecraft")
        elif message.text=="/sendcommandtominecraft":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="minecraftmessagesend"
                bot.send_message(message.chat.id, "Теперь введите команду (или /back для отмены)")
        elif message.text=="/commandsendermode":
            if not message.chat.id in DATA["admin"]:
                bot.send_message(message.chat.id, "Вы должны быть одним из админов чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="minecraftcommandsendermode"
                bot.send_message(message.chat.id, "Теперь вводите команды (или /back для завершения)")



        elif message.text=="/downloadfile":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы должны зайти чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="file_download"
                bot.send_message(message.chat.id, "Теперь введите ссылку на файл")
        elif message.text=="/downloadtext":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы должны зайти чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="text_download"
                bot.send_message(message.chat.id, "Теперь введите ссылку на сайт")
        elif message.text=="/downloadfiledrive":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы должны зайти чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="file_download_disk"
                bot.send_message(message.chat.id, "Теперь введите ссылку на файл")
        elif message.text=="/downloaddirdrive":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы должны зайти чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="dir_download_disk"
                bot.send_message(message.chat.id, "Теперь введите ссылку на папку")
        elif message.text=="/downloadmagnet":
            if not message.chat.id in DATA["usersLogin"]:
                bot.send_message(message.chat.id, "Вы должны зайти чтобы использовать это")
            else:
                DATA["usersNOW"][message.chat.id]="magnet_download"
                bot.send_message(message.chat.id, "Теперь введите magnet ссылку")


        elif not message.chat.id in DATA["usersLogin"]:
            bot.send_message(message.chat.id, """Привет! Это \"локальный\" бот для загрузки файлов интернета.
Используй /login чтобы пользоваться.
Или /logout чтобы выйти из пользования.

Лично для удобства админов - /admin
""")
        else:
            bot.send_message(message.chat.id, "Чтобы скачать что-либо нужно использовать\n/downloadfile для скачивания файла\n/downloadtext для скачивания сайта\n/downloadfiledrive для скачивания файла с внутреннего диска бота\n/downloaddirdrive для скачивания папки по очереди с внутреннего диска бота\n/downloadmagnet для скачивания с magnet ссылки\n\nЛично для удобства админов - /admin")

    elif DATA["usersNOW"][message.chat.id] == "write_code":
        DATA["usersNOW"][message.chat.id] = "None"
        if message.text.strip() == DATA["loginpass"]:
            DATA["loginpass"]=''.join(map(chr,[rand(ord('A'), ord('Z')) for i in range(12)]))
            DATA["usersLogin"].add(message.chat.id)
            bot.send_message(message.chat.id, "Успешно")
            for ind in DATA["admin"].copy():
                sleep(1)
                bot.send_message(ind, "Пользователь " + str(message.chat.id) + " вошёл")
        else:
            bot.send_message(message.chat.id, "Неуспешно")

    elif DATA["usersNOW"][message.chat.id] == "write_code_admin":
        DATA["usersNOW"][message.chat.id] = "None"
        if message.text.strip() == adminpass:
            DATA["admin"].add(message.chat.id)
            bot.send_message(message.chat.id, "Успешно - ещё раз /admin для просмотра комманд")
        else:
            bot.send_message(message.chat.id, "Неуспешно")

    elif DATA["usersNOW"][message.chat.id] == "sure_logout":
        if message.text.strip() == "да":
            DATA["usersNOW"][message.chat.id] = "None"
            DATA["usersLogin"].remove(message.chat.id)
            bot.send_message(message.chat.id, "Вы успешно вышли")
        else:
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Отменено")

    elif DATA["usersNOW"][message.chat.id] == "sure_fullstop":
        if message.text.strip() == "да":
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Выключаемся...")
            if useupd:
                dump(DATA, open("datafile.dat", 'wb'))
            bot.stop_bot()
        else:
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Отменено")

    elif DATA["usersNOW"][message.chat.id] == "text_download":
        DATA["usersNOW"][message.chat.id] = "None"
        link = message.text.strip()
        
        number = ''.join(map(chr,[rand(ord('0'), ord('9')) for i in range(5)]))
        bot.send_message(message.chat.id, "Ждите, ваш талон - " + number)
        try:
            if link[:4] == "http":
                bot.send_document(message.chat.id, bytes(get(link).text, encoding="utf-8"), visible_file_name = "page" + number + ".html")
            else:
                bot.send_message(message.chat.id, "Невозможно загрузить файл с талоном " + number)
        except:
            bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number)

    elif DATA["usersNOW"][message.chat.id] == "file_download":
        DATA["usersNOW"][message.chat.id] = "None"
        link = message.text.strip()
        
        number = ''.join(map(chr,[rand(ord('0'), ord('9')) for i in range(5)]))
        bot.send_message(message.chat.id, "Ждите, ваш талон - " + number)
        file_data = None
        if link[:4] == "http":
            try:
                file_data = get(link).content
            except:
                pass
        if file_data != None and len(file_data) > 0:
            if len(file_data) < MAXSIZE:
                bot.send_document(message.chat.id, file_data, visible_file_name = "file" + number + "." + link.split('.')[-1])
            else:
                bot.send_message(message.chat.id, "Файл с талоном "+number+" превышает телеграммовский размер, так что отсылаю частями:")
                if not message.chat.id in DATA["hasFP"]:
                    bot.send_document(message.chat.id, open("/telegram_bots/fp.zip", 'rb').read(), visible_file_name = "fb.zip", caption = "Эта утилита поможет вам восстановить файл, нужно лишь сделать так:\n.\\fileparter -n <количество_частей> -f название файла без part0/1/2... --torecieve -B 1000000")
                    DATA["hasFP"].add(message.chat.id)
                    sleep(1.5)
                i=0
                while i < len(file_data):
                    try:
                        bot.send_document(message.chat.id, file_data[i:i+MAXSIZE], visible_file_name = "file" + number + "." + link.split('.')[-1] + "part" + str(i//MAXSIZE))
                    except:
                        pass
                    i += MAXSIZE
                    sleep((len(file_data) + 1) / (50 * 1024 * 1024) * 4)
                bot.send_message(message.chat.id, "Файл с талоном "+number+" отправился успешно")
        else:
            bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number)

    elif DATA["usersNOW"][message.chat.id] == "file_download_disk":
        DATA["usersNOW"][message.chat.id] = "None"
        link = message.text.strip()
        if '..' in link:
            bot.send_message(message.chat.id, "Вам запрещено скачивать данный файл")
        else:
        
            number = ''.join(map(chr,[rand(ord('0'), ord('9')) for i in range(5)]))
            bot.send_message(message.chat.id, "Ждите, ваш талон - " + number)
            file_self = None
            try:
                file_self = open("/telegram_bots/files/"+link, 'rb')
            except:
                bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number + ", его не существует")
            if file_self != None:
                file_data = file_self.read(MAXSIZE)
                if os.stat("/telegram_bots/files/"+link).st_size <= MAXSIZE:
                    bot.send_document(message.chat.id, file_data, visible_file_name = "file" + number + "." + link.split('.')[-1])
                else:
                    bot.send_message(message.chat.id, "Файл с талоном "+number+" превышает телеграммовский размер, так что отсылаю частями:")
                    if not message.chat.id in DATA["hasFP"]:
                        bot.send_document(message.chat.id, open("/telegram_bots/fp.zip", 'rb').read(), visible_file_name = "fb.zip", caption = "Эта утилита поможет вам восстановить файл, нужно лишь сделать так:\n.\\fileparter -n <количество_частей> -f название файла без part0/1/2... --torecieve -B 1000000")
                        DATA["hasFP"].add(message.chat.id)
                        sleep(1.5)
                    i=0
                    while file_data:
                        try:
                            bot.send_document(message.chat.id, file_data, visible_file_name = "file" + number + "." + link.split('.')[-1] + "part" + (str(i).rjust(6).replace(' ', '0')))
                        except:
                            pass
                        i += 1
                        sleep((len(file_data) + 1) / (50 * 1024 * 1024)) # * i)
                        file_data = file_self.read(MAXSIZE // 4)
                    bot.send_message(message.chat.id, "Файл с талоном "+number+" отправился успешно")
    
    elif DATA["usersNOW"][message.chat.id] == "dir_download_disk":
        DATA["usersNOW"][message.chat.id] = "None"
        linkdir = message.text.strip()
        if '..' in linkdir or '~' in linkdir:
            bot.send_message(message.chat.id, "Вам запрещено скачивать данную папку")
        else:
            files_list = []
            for root, dirs, files in os.walk("/telegram_bots/files/"+linkdir):  
                files_list += [root[len("/telegram_bots/files/"):].replace('\\', '/') + "/" + x for x in files]
            bot.send_message(message.chat.id, "Идет загрузка папки " + linkdir + " всего файлов " + str(len(files_list)))
            for link in files_list:
                number = ''.join(map(chr,[rand(ord('0'), ord('9')) for i in range(5)]))
                bot.send_message(message.chat.id, "Талон файла " + link + " - " + number)
                file_self = None
                try:
                    file_self = open("/telegram_bots/files/"+link, 'rb')
                except:
                    bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number + ", внутренний сбой")
                if file_self != None:
                    file_data = file_self.read(MAXSIZE)
                    if os.stat("/telegram_bots/files/"+link).st_size <= MAXSIZE:
                        bot.send_document(message.chat.id, file_data, visible_file_name = "file" + number + "." + link.split('.')[-1])
                    else:
                        bot.send_message(message.chat.id, "Файл с талоном "+number+" превышает телеграммовский размер, попробуйте отправить обычным способом")
                    sleep((len(file_data) + 1) / (50 * 1024 * 1024) * 4)

    elif DATA["usersNOW"][message.chat.id] == "magnet_download":
        DATA["usersNOW"][message.chat.id] = "None"
        link = message.text.strip()
        if '..' in link or '~' in link:
            bot.send_message(message.chat.id, "Вам запрещено скачивать данный файл")
        else:
            number = ''.join(map(chr,[rand(ord('0'), ord('9')) for i in range(5)]))
            bot.send_message(message.chat.id, "Ждите, ваш талон - " + number)
            try:
                hsh = link[link.index("xt=urn:btih:") + len("xt=urn:btih:"):link.index("&")]
                if len(hsh) > 15 and qbittorrentclient.download_from_link(link, savepath = '/'.join(__file__.replace('\\','/').split('/')[:-1])+"/files/"+hsh+"/", category = hsh) != None:
                    bot.send_message(message.chat.id, "Талон " + number + " поставился на закачку")
                    realhsh = qbittorrentclient.torrents(category = hsh)[0]["hash"]
                    while qbittorrentclient.get_torrent(realhsh)["completion_date"]==-1:
                        sleep(10)
                    bot.send_message(message.chat.id, "Талон " + number + " скачался")

                    files_list = []
                    for root, dirs, files in os.walk("/telegram_bots/files/"+hsh):  
                        files_list += [root[len("/telegram_bots/files/"):].replace('\\', '/') + "/" + x for x in files]
                    towrite = "Список файлов талона " + number + ":\n"+'\n'.join(files_list)
                    i=0
                    while i<len(towrite):
                        bot.send_message(message.chat.id, towrite[i:i+MAXMESSAGESIZE])
                        i += MAXMESSAGESIZE
                        sleep(1)
                else:
                    bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number)
            except:
                bot.send_message(message.chat.id, "Не удалось загрузить файл с талоном " + number)

    elif DATA["usersNOW"][message.chat.id] == "get_data_from_hashtorrent":
        DATA["usersNOW"][message.chat.id] = "None"
        try:
            bot.send_message(message.chat.id, str(qbittorrentclient.get_torrent(message.text.strip())))
        except:
            bot.send_message(message.chat.id, "Не удалось узнать")

    elif DATA["usersNOW"][message.chat.id] == "sure_deleteall":
        if message.text.strip() == "да":
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, str(qbittorrentclient.delete_all()))
        else:
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Отменено")
    
    elif DATA["usersNOW"][message.chat.id] == "sure_permanentdeleteall":
        if message.text.strip() == "да":
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, str(qbittorrentclient.delete_all_permanently()))
            os.system("rmdir /telegram_bots/files/*")
        else:
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Отменено")

    elif DATA["usersNOW"][message.chat.id] == "block_user":
        DATA["usersNOW"][message.chat.id] = "None"
        tointmes = None
        try:
            tointmes = int(message.text.strip())
        except:
            bot.send_message(message.chat.id, "Отменено")
        if tointmes != None:
            if tointmes in DATA["usersLogin"]:
                DATA["usersLogin"].remove(tointmes)
                if tointmes in DATA["hasFP"]:
                    DATA["hasFP"].remove(tointmes)
                bot.send_message(message.chat.id, "Пользователь " + str(tointmes) + " заблокирован")
            else:
                bot.send_message(message.chat.id, "Пользователь " + str(tointmes) + " не найден или ещё не вошёл")

    elif DATA["usersNOW"][message.chat.id] == "sure_block_user_all":
        if message.text.strip() == "да":
            DATA["usersNOW"][message.chat.id] = "None"
            DATA["usersLogin"].clear()
            DATA["hasFP"].clear()
            bot.send_message(message.chat.id, "Ок")
        else:
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Отменено")
    
    elif DATA["usersNOW"][message.chat.id] == "minecraftmessagesend":
        DATA["usersNOW"][message.chat.id] = "None"
        if message.text.strip() == "/back":
            bot.send_message(message.chat.id, "Отменено")
        elif minecraftconwrite != None:
            minecraftconwrite.write(message.text.strip() + "\n")
            minecraftconwrite.flush()

    elif DATA["usersNOW"][message.chat.id] == "minecraftcommandsendermode":
        if message.text.strip() == "/back":
            DATA["usersNOW"][message.chat.id] = "None"
            bot.send_message(message.chat.id, "Завершено")
        elif minecraftconwrite != None:
            minecraftconwrite.write(message.text.strip() + "\n")
            minecraftconwrite.flush()

init()
bot.infinity_polling()
