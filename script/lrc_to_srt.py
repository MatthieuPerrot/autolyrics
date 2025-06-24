from os import listdir
import re

def getTagValue(lines, tag):
    for l in lines:
        temp = re.search("^\[{}:.*\]".format(tag), l)
        if temp!=None:
            return temp.string[2+len(tag):-1]
    return None

def lrcTimestampToInt(timestamp, offset=0):
    if timestamp==None:
        return
    if not "." in timestamp:
        timestamp = timestamp.replace("]", ".00]")
    timestamp = timestamp.replace("[","").replace("]","").replace(":",".")
    msecFac = 10 if len(timestamp)==2 else 1
    num = timestamp.split(".")
    return int(num[0])*60000 + int(num[1])*1000 + int(num[2])*msecFac - offset

def intToSrtTimestamp(time):
    min = time//60000
    time = time%60000
    sec = time//1000
    msec = time%1000
    return "00:{}:{},{}".format(str(min).zfill(2), str(sec).zfill(2), str(msec).zfill(3))

def splitTimstampText(line, offset=0):
    stamps = re.findall("\[\d{1,2}:\d{1,2}\..{2,3}\]", line)
    stamps2 = re.findall("\[\d{1,2}:\d{1,2}\]", line)
    stamps = stamps + stamps2
    intStamps = []
    stampLen = 0
    for s in stamps:
        stampLen += len(s)
        if not "." in s: s = s.replace("]", ".00]")
        intStamps.append(lrcTimestampToInt(s, offset=offset))
    return intStamps, line[stampLen:]

def insertLine(lrc, line):
    for i in range(len(lrc)):
        if lrc[i][0]>line[0]:
            lrc.insert(i, line)
            return
    lrc.append(line)

def getLyrics(path, encoding=None):
    if(encoding==None):
        File = open(path)
    else:
        File = open(path, encoding)
    line = File.read().split("\n")
    offset = getTagValue(line, "offset")
    offset = 0 if offset==None else int(offset)

    lrc = []

    for l in line:
        stamps, text = splitTimstampText(l, offset=offset)
        if text=="": text=" "
        for s in stamps:
            insertLine(lrc, [s, text])


    if len(lrc)>0 and lrc[-1][1]!=" ":
        length = getTagValue(line, "length")
        lrc.append([lrcTimestampToInt("["+length+"]", offset=offset) if length!=None else lrc[-1][0]+5000," "])

    return lrc

def createSRT(path, lrc):
    Out = open(path, "w")
    for i in range(len(lrc)-1):
        try:
            Out.write(str(i+1)+"\n")
            Out.write("{} --> {}\n".format(intToSrtTimestamp(lrc[i][0]), intToSrtTimestamp(lrc[i+1][0])))
            Out.write(lrc[i][1])
            Out.write("\n\n")
        except:
            print("An Error occured at {} on line {}".format(path, i+1))

def convertFile(f, In, Out, encoding=None):
    if not f[-4:]==".lrc":
            return True
    try:
        Lyrics = getLyrics(In+"/"+f, encoding)
        createSRT(Out+"/"+f[:-4]+".srt", Lyrics)
        print("converted \"{}\"".format(f))
        return True
    except Exception as e:
        print("!!! ERROR occured at File \"{}\"".format(f))
        print(e)
        return False

def convertDirectory():
    print("Enter Input-Directory")
    In = input()
    print("Enter Output-Directory")
    Out = input()
    Files = listdir(In)
    for f in Files:
        convertFile(f, In, Out)

convertDirectory()
