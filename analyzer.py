import os
import datetime

myPath=os.getcwd()
files=os.listdir(myPath)

for f in files:
    if f.endswith("xyz"):
        print(f)
        fx=open(f)
        lines=fx.readlines()
        fx.close()
        data=((lines[0]).split(","))
        print(data)
        mytype=data[0]
        myname=data[1]
        
        print(mytype+ "--"+ myname)
        mynewfilename=(mytype+"-"+str(datetime.date.today())+"-"+myname+"-"+(f.replace("'","-")).replace(".xyz",".csv"))
        new_file=open(mynewfilename,"w")
        i=0
        for line in lines:
            if i==0:
                print(line)
            else:
                new_file.write(line)
                print(i,line)
            i=i+1
        new_file.close()
        os.remove(f)
print(" ")