
Requirements to run the tests :
 - Ant - to build the project
 - Ivy - to resolve dependencies
 - Java - version 1.6. [ Important Yosemite removes Java 1.6 from your Mac. Please install Java version 1.6 or tests can fail.]

You can install Ant and Ivy via the following methods :
1) Download them from ant.apache.com and ant.apache.com/ivy. Untar them to a folder of your choice and set CLASSPATH, PATH etc to this folder. You will have
to copy the ivy jar to your ant/lib folder.
2) Easier method  would be install it via package manager for your OS. On OS X you can just do ```brew install ant --with-ivy```


Instructions to run the script :

1) You need to set following environment variables :
 AWS_ACCESS_KEY_ID, AWS_ACCESS_SECRET, SAUCE_USER_NAME, SAUCE_KEY

2) Launch a new YOMP instance.

3) You have to run selenium bash script in which is located in behavioural/YOMP folder.
 Path is : products/YOMP/tests/java/behavioral/YOMP/run_selenium_test.

4) For running script you have run command like :
- Sample command 1 : ./run_selenium_tests -s|--server <YOMP-server-url> -o|--os "WINDOWS 8" -b|--browser "FIREFOX" -u|--usertype "FIRST_TIME"
(Using "FIRST_TIME" we are selecting first time user for running script)
- Sample command 2 : ./run_selenium_tests -s|--server <YOMP-server-url> -o|--os "WINDOWS 8" -b|--browser "FIREFOX" -u|--usertype "ADVANCED"
(Using "ADVANCED" we are selecting advance user for running script)