Requirements to run the tests :
 * Maven
 * Java - version 1.7 and above

You can install Maven via the following methods :
* Download them from http://maven.apache.org/download.cgi. Untar them to a folder of your choice.
* On OS X, you can install maven with `brew install maven`

Upload APK in Sauce Storage by following command :
* Download apk
* Run this command :
`curl -u $SAUCE_USER_NAME:$SAUCE_KEY -X POST "http://saucelabs.com/rest/v1/storage/$SAUCE_USER_NAME/taur-app-release.apk?overwrite=true" -H "Content-Type: application/octet-stream" --data-binary @<path_where_apk_present>/taur-app-release.apk`


Instructions to run the script :

1. Set following environment variables :
 `SAUCE_USER_NAME`, `SAUCE_KEY`

2. For running script use following commands:
 * `mvn eclipse:eclipse`
 * `mvn clean`
 * Sample command 1:
 mvn install -D deviceName="Android Emulator" -D version="4.4" -D sauceUserName=$SAUCE_USER_NAME -D sauceAccessKey=$SAUCE_KEY
 * Sample command 2:
 mvn install -D deviceName="Google Nexus 7C Emulator" -D version="4.4" -D sauceUserName=$SAUCE_USER_NAME -D sauceAccessKey=$SAUCE_KEY

3. For watching running script you login into sauce lab using this url https://saucelabs.com/tests, in test section you can see the live video of running tests.
