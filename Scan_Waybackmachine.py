import re
import requests
from bs4 import BeautifulSoup
import time
import sys
import json

non_bmp_map = dict.fromkeys(range(0x10000, sys.maxunicode + 1), 0xfffd)

yt_dl_channels_file = "youtube-dl-channels.txt" #list of youtube channel urls (with /videos on the end)
archive_file_filename = "youtube-dl-archive.txt" #list of already downloaded youtube IDs, in the ytdl format
failure_count_thres = 10 #If pings to waybackmachine fail more than this, compare to failure thresh
failure_fraction_thresh = .7 #threshold that decides if waybackmachine is being non-responsive for a url
wayback_machine_scan_interval = 15 #Period in days, between 1 day and 15 days
today_date = "20210712" #today's date as a string. I know it's bad but it works



valid_wayback_pages = "wayback_urls.txt"
possibly_valid_ids = "possibly_valid_ids.txt"
cleaned_possibly_valid_ids = "cleaned_possibly_valid_ids.txt"
yt_scraped_data = "video_scraped_info.txt"
output_file = "output_url_results.txt"


def import_channels():
    channel_array = []
    with open(yt_dl_channels_file,"r",encoding="utf-8") as file:
        for line in file:
            if "http" in line:
                channel_array.append(line.replace("	","")
                                     .replace("/videos","")
                                     .replace("#","")
                                     .replace("\n",""))
    return channel_array


def get_waybackmachine_pages(channel):
    #url = f"http://archive.org/wayback/available?url={channel}"
    valid_pages = []
    current_date = "20050101"#current_date = "20050101"
    failure_counter = 0
    success_counter = 0
    critical_failure_counter = 0
    critical_failure_counter_thresh = 3
    print(f"Currently scanning waybackmachine for {channel}")
    while int(today_date) > int(current_date):
        url = f"http://archive.org/wayback/available?url={channel}&timestamp={current_date}"
        #print(url)
        
        response = requests.get(url)
        soup = BeautifulSoup(response.text,'html.parser')
        relevant_data = str(soup)
        #print(relevant_data)
        try:
            json_data = json.loads(relevant_data)
            #print(json_data["archived_snapshots"])
                
            if json_data["archived_snapshots"] == {}:
                print(f"Failure #{failure_counter+1}, failure rate {round((failure_counter+1)/(failure_counter+1+success_counter),3)}")
                failure_counter +=1
                if failure_counter > failure_count_thres:
                    if failure_counter/(failure_counter+success_counter) > failure_fraction_thresh:
                        break
            elif json_data["archived_snapshots"] != {}:
                success_counter +=1
                if json_data["archived_snapshots"]["closest"]["url"] not in valid_pages:
                    valid_pages.append(json_data["archived_snapshots"]["closest"]["url"])
                if int(str(json_data["archived_snapshots"]["closest"]["timestamp"][0:8]))> int(current_date):
                    current_date = str(json_data["archived_snapshots"]["closest"]["timestamp"][0:8]) #Would greatly reduce time, but sometimes reandomly breaks...
        except Exception as e:
            print(f"Critical Error: {e}")
            critical_failure_counter +=1
            if critical_failure_counter >= critical_failure_counter_thresh:
                print("Hit critical error thresh, pausing script. Something may be wrong.")
                time.sleep(99999)
                
        if int(current_date[6:8])>=(27-wayback_machine_scan_interval):#if month rollover:
            #print("case1")
            if int(current_date[4:6])>=13:#if year rollover:
                #print("case2")
                current_date = str(int(current_date[0:4])+1)+"0101"
            else:
                #print("case3")
                month = int(current_date[4:6])+1
                month_str = str(month)
                if len(month_str)<2:
                    month_str = "0"+month_str
                current_date = current_date[0:4]+str(month_str)+"01"
        else:
            #print("case4")
            day = int(current_date[6:8])+wayback_machine_scan_interval
            day_str = str(day)
            if len(day_str)<2:
                day_str = "0"+day_str
            current_date = current_date[0:6] + str(day_str)
        #print("new current scan date",current_date)
        time.sleep(0.75)
    return valid_pages


def write_valid_wayback_urls(valid_pages):
    with open(valid_wayback_pages,"a+",encoding="utf-8") as writing_file:
        for item in valid_pages:
            writing_file.write(str(item)+"\n")


def read_channel_urls():
    urls = []
    with open(valid_wayback_pages,"r",encoding="utf-8") as readfile:
        for line in readfile:
            urls.append(line.replace("\n",""))
    return urls


def read_sites(url_list):
    timer_start = time.time()
    counter = 0
    
    for url in url_list:
        possible_items = []
        counter += 1
        temp_possible_items = []
        response = requests.get(url)
        #print(response)
        soup = BeautifulSoup(response.text, 'html.parser')#.translate(non_bmp_map)
        #print(soup)
        for line in str(soup).split("\n"):
            if "youtube.com" in line:
                for item in line.split("/"):
                    if len(item) == 11:
                        if "youtube.com" not in item:
                            temp_possible_items.append(item)
                for item in line.split('"'):
                    if "watch?v=" in item:
                        if len(item.split("watch?v=")[-1]) == 11:
                            temp_possible_items.append(item.split("watch?v=")[-1])
                        else:
                            if "&amp;" in item.split("watch?v=")[-1]:
                                temp_possible_items.append(item.split("watch?v=")[-1].split("&amp")[0])
                            elif "\u0026" in item.split("watch?v=")[-1]:
                                temp_possible_items.append(item.split("watch?v=")[-1].split("\\u0026")[0])
                            else:
                                temp_possible_items.append(item.split("watch?v=")[-1][0:11])
                                #print(item.split("watch?v=")[-1][0:11])
        print(f"{len(temp_possible_items)} possible new items from {url}")
        print(f"{counter} items done of {len(url_list)}. {round((time.time()-timer_start)/counter,4)} sec per item")
        for yt_id in temp_possible_items:
            if yt_id not in possible_items:
                if "src" not in yt_id and "ytimg" not in yt_id and "login" not in yt_id:
                    if "\\n" not in yt_id and "<" not in yt_id and ">" not in yt_id and " " not in yt_id:
                        if "," not in yt_id and "." not in yt_id:
                            possible_items.append(yt_id)
        print(f"{len(possible_items)} items in master list")
        #print(temp_possible_items)
        time.sleep(.75)
        #print(possible_items)
        with open(possibly_valid_ids,"a+",encoding="utf-8") as output_file:
            for item in possible_items:
                output_file.write(item+"\n")
    #print("Writing url data to file now")

def load_long_list():
    long_list = []
    with open(possibly_valid_ids,"r+",encoding="utf-8") as longfile:
        for line in longfile:
            long_list.append(line.replace("\n",""))
    return long_list

def remove_duplicates(long_list):
    short_list = []
    counter = 0
    for item in long_list:
        counter +=1
        if counter % 1000 == 0:
            print(f"{counter} of {len(long_list)}")
        if item not in short_list:
            short_list.append(item)
    return short_list

def write_results(short_list):
    with open(cleaned_possibly_valid_ids,"a+",encoding="utf-8") as out_file:
        for item in short_list:
            out_file.write("https://www.youtube.com/watch?v="+item+"\n")

def find_resume_location():
    resume_int = 0
    with open(yt_scraped_data,"w+",encoding = "utf-8") as index_data:
        for line in index_data:
            if int(line.split(" _,_ ")[0]) > resume_int:
                resume_int = int(line.split(" _,_ ")[0])
    print("Resuming at ",resume_int)
    return resume_int

def import_files():
    urls = []
    archive = []
    with open(archive_file_filename,"r") as datafile:
        for line in datafile:
            archive.append("https://www.youtube.com/watch?v="+line.replace("\n","").replace("youtube ",""))
    with open(cleaned_possibly_valid_ids,"r") as datafile:
        for line in datafile:
            if line.replace("\n","") not in archive:
                urls.append(line.replace("\n",""))
    return urls


def download_youtube_pages(url_int,urls):
    try:
        response = requests.get(urls[url_int])
        #response = requests.get("https://www.youtube.com/watch?v=BRSr5jnRI10")
        #print(response)
        soup = BeautifulSoup(response.text, 'html.parser')
        #print(soup)
        if '"isUnlisted":true' in str(soup):
            #print("Unlisted video here!")
            time.sleep(.75)
            relevant_data = str(soup).split("""[{"@type": "ListItem", "position": 1, "item":""")[1].split("""}}]}</script>""")[0]
            Channel_URL = relevant_data.split(": \"")[1].split("\", \"name\"")[0].replace("\\","")
            Channel_Name = relevant_data.split("name\": \"")[1].replace("\"","")
            Views = str(soup).split("{\"viewCount\":{\"simpleText\":\"")[1].split("\"},\"shortViewCount\"")[0]
            try:
                Subscribers = str(soup).split("\"subscriberCountText\":{\"accessibility\":{\"accessibilityData\":{\"label\":\"")[1].split("\"}},\"simpleText\":\"")[0]
                if "K" in Subscribers:
                    Subscribers_Int = int(float(Subscribers.split("K")[0])*1000)
                    New_Subscribers_String = str(Subscribers_Int) +  " subscribers"
                    Subscribers = New_Subscribers_String
                if "M" in Subscribers:
                    Subscribers_Int = int(float(Subscribers.split("M")[0])*1000*1000)
                    New_Subscribers_String = str(Subscribers_Int) +  " subscribers"
                    Subscribers = New_Subscribers_String
                if " million" in Subscribers:
                    Subscribers_Int = int(float(Subscribers.split(" million")[0])*1000*1000)
                    New_Subscribers_String = str(Subscribers_Int) +  " subscribers"
                    Subscribers = New_Subscribers_String
            except:
                Subscribers = str(1) + " subscribers"
            amalgam_string = f"{url_int} _,_ {Channel_Name} _,_ {Channel_URL} _,_ {Subscribers} _,_ {Views} _,_ {urls[url_int]}\n"
            with open(yt_scraped_data,"a+",encoding = "utf-8") as IndexData:
                IndexData.write(amalgam_string)
            print(url_int,urls[url_int])
            print(amalgam_string)
    except Exception as e:
        print("###################################################################################################################")
        print(f"Error downloading video, {e}")


def load_indexdata():
    imported_array = []
    counter = 0
    with open(yt_scraped_data,"r",encoding = "utf-8") as index_file:
        for line in index_file:
            imported_array.append(line.replace("\n","").split(" _,_ "))
            counter +=1
            #if counter > 100000:
                #break
    return imported_array


def parse_indexdata(imported_array):
    organized_channels = []
    organized_urls = []
    video_count_array = []
    video_data_array = []
    #organizing content by channel
    counter = 0
    for item in imported_array:
        counter +=1
        if counter %100 == 0:
            print(counter)
        if item[2] not in organized_channels:
            organized_channels.append(item[2])
            organized_urls.append(item[1])
            video_count_array.append(1)
            video_data_array.append([item[5]])
        else:
            video_count_array[organized_channels.index(item[2])] +=1
            video_data_array[organized_channels.index(item[2])] = video_data_array[organized_channels.index(item[2])] + [item[5]]
    #print(organized_channels,organized_urls)
    #print(video_count_array,video_data_array)
    return organized_channels,organized_urls,video_count_array,video_data_array


def report_data(organized_channels,organized_urls,video_count_array,video_data_array):
    amalgam_array = []
    for i in range(len(organized_channels)):
        #print(organized_channels[i])
        #print(video_count_array[i])
        #print(video_data_array[i])
        amalgam_array.append([organized_channels[i],organized_urls[i],video_count_array[i],video_data_array[i]])          #Change this to include video data
    amalgam_array.sort(key = lambda x: x[2], reverse = True)
    #for item in range(20):
        #print(amalgam_array[item])
    return amalgam_array


def import_channel_data():
    channels = []
    names = []
    with open(yt_dl_channels_file,"r",encoding = "utf-8") as channel_file:
        for line in channel_file:
            if "http" in line:
                channels.append(line.replace("\t","").replace("\n","").replace("#","").replace("/videos","").replace("\t",""))
                names.append(line.replace("\n","").replace("#","").replace("/videos","").split("/")[-1])
    #print(channels)
    #print(names)
    return channels,names


def report_channels_shared(channels,names,amalgam_array):
    channel_comparison_results = []
    print("######################################################################")
    for i in range(len(amalgam_array)):
        #print(amalgam_array[i][0])
        for j in range(len(channels)):
            print(amalgam_array[i][0])
            print(amalgam_array[i][1])
            if amalgam_array[i][0] == channels[j]:
                print(f"1, {amalgam_array[i][0]},{channels[j]},{len(amalgam_array[i][3])}") #Index 3 reports videos
                for k in amalgam_array[i][3]:
                    channel_comparison_results.append(f"1 _,_ {amalgam_array[i][0]} _,_{channels[j]} _,_ {k}")
            elif amalgam_array[i][1] == names[j]:
                print(f"2, {amalgam_array[i][1]},{names[j]},{len(amalgam_array[i][3])}")
                for k in amalgam_array[i][3]:
                    channel_comparison_results.append(f"1 _,_ {amalgam_array[i][0]} _,_{channels[j]} _,_ {k}")
            elif amalgam_array[i][0].split("/")[-1] == names[j]:
                print(f"""3, {amalgam_array[i][0].split("/")[-1]},{names[j]},{len(amalgam_array[i][3])}""")
                for k in amalgam_array[i][3]:
                    channel_comparison_results.append(f"1 _,_ {amalgam_array[i][0]} _,_{channels[j]} _,_ {k}")
            else:
                pass
    return channel_comparison_results


def write_results_to_file(array):
    with open(output_file,"w+",encoding = "utf-8") as results_file:
        for item in array:
            if "watch?v=" in item:
                results_file.write(str(item).split(" _,_ ")[-1]+"\n")

if __name__ == "__main__":
    channel_list = import_channels()
    print(f"{len(channel_list)} channels to scan")#
    counter = 0
    for channel in channel_list:
        valid_pages = get_waybackmachine_pages(channel)
        write_valid_wayback_urls(valid_pages)
        valid_pages = get_waybackmachine_pages(channel+"/videos")
        write_valid_wayback_urls(valid_pages)
        counter += 1
    url_list = read_channel_urls()
    read_sites(url_list)
    long_list = load_long_list()
    short_list = remove_duplicates(long_list)
    write_results(short_list)
    resume_int = find_resume_location()
    urls = import_files()
    timer_start = time.time()
    counter = 0
    for url_int in range(resume_int,len(urls)):
        download_youtube_pages(url_int,urls)
        time.sleep(0.01)
        counter += 1
    imported_array = load_indexdata()
    organized_channels,organized_urls,video_count_array,video_data_array = parse_indexdata(imported_array)
    amalgam_array = report_data(organized_channels,organized_urls,video_count_array,video_data_array)
    channels,names = import_channel_data()
    channel_comparison_results = report_channels_shared(channels,names,amalgam_array)
    write_results_to_file(channel_comparison_results)

