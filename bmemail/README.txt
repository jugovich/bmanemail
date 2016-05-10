open index.html in /src/build/html/index.html to see full project documentation, report and readme

readme is also below.


README
======

Steps to get this project working on your machine

  1) First download and install python 2.7 http://www.python.org/download/
  
  2) Download and install setup-tools for python 2.7 to install required libraries for cardsharp 
     http://pypi.python.org/pypi/setuptools#downloads 
  
  3) Open a cmd terminal
  
  4) add the pyhton scripts directory (below is if you installed to c:\) to your path
  
     >>> path = %path%;c:\python27\scripts
     
  5) issue the following commands to install libraries with setup-tools
     
     >>> easy_install xlrd
     >>> easy_install xlwt
     >>> easy_install xlutils
     >>> easy_install pyyaml
     
  6) download and install 7-zip http://www.7-zip.org/download.html
  
  7) change the path in /src/cardsharp/csharp.config to where you installed 7-zip
     
     >>> [csharp]
	 >>> 7zip_exe = c:\7-Zip\7z.exe
	 
  8) See http://cardsharp.norc.org/cardsharp/wiki/tutorial/tutorial.html#setting-up-cardsharp
     for more info on cardsharp setup if needed 
     
  9) Make sure the weka jar file is in your classpath
  
  10) navigate to *install_path*/src/ and type the following
      
      >>> event.py run
      
      or
      
      using eclipse setup a run configuration with on event.py with run as the arguement
      
   11) Take a break because the program takes about 5 minutes to run