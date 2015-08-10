module.exports = function(grunt) {
    var username = process.env.SAUCE_USERNAME,
        key =      process.env.SAUCE_ACCESS_KEY,

        name = 'YOMP JS Unit Tests',

        port = 9999,
        urlPrefix = 'http://127.0.0.1:' + port + '/tests/js/',

        // SYNC: https://YOMPhub.com/YOMPSolutions/YOMP/wiki/Browser-Support
        browsers = [
            // Android
            {
                "browserName":          "android",
                "deviceName":           "Android Emulator",
                "device-orientation":   "portrait",
                "platform":             "Linux",
                "version":              "5.1"
            },
            {
                "browserName":          "android",
                "deviceName":           "Android Emulator",
                "device-orientation":   "portrait",
                "platform":             "Linux",
                "version":              "4.0"
            },

            // Chrome
            {
                "browserName":  "chrome",
                "platform":     "Windows 8.1",
                "version":      "41.0"
            },
            {
                "browserName":  "chrome",
                "platform":     "OS X 10.10",
                "version":      "41.0"
            },
            {
                "browserName":  "chrome",
                "platform":     "Linux",
                "version":      "41.0"
            },

            // Firefox
            {
                "browserName":  "firefox",
                "platform":     "Windows 8.1",
                "version":      "37.0"
            },
            {
                "browserName":  "firefox",
                "platform":     "OS X 10.10",
                "version":      "36.0"
            },
            {
                "browserName":  "firefox",
                "platform":     "Linux",
                "version":      "37.0"
            },

            // Internet Explorer
            {
                "browserName":  "internet explorer",
                "platform":     "Windows 8.1",
                "version":      "11.0"
            },
            {
                "browserName":  "internet explorer",
                "platform":     "Windows 8",
                "version":      "10.0"
            },
            {
                "browserName":  "internet explorer",
                "platform":     "Windows 7",
                "version":      "9.0"
            },

            // iOS
            {
                "browserName":          "iphone",
                "deviceName":           "iPad Simulator",
                "device-orientation":   "portrait",
                "platform":             "OS X 10.10",
                "version":              "8.2"
            },
            {
                "browserName":          "iphone",
                "deviceName":           "iPhone Simulator",
                "device-orientation":   "portrait",
                "platform":             "OS X 10.10",
                "version":              "8.2"
            },

            // Safari
            {
                "browserName":  "safari",
                "platform":     "OS X 10.10",
                "version":      "8.0"
            }
        ],

        urls = [
            urlPrefix + 'unit/runner.lib.YOMPApi.html',
            urlPrefix + 'unit/runner.collections.html',
            urlPrefix + 'unit/runner.models.html',
            urlPrefix + 'unit/runner.views.html'
        ];

    grunt.initConfig({
        connect: {
            server: {
                options: {
                    hostname:   '*',
                    port:       port
                }
            }
        },
        "saucelabs-mocha": {
            all: {
                options: {
                    browsers: browsers,
                    concurrency: 6,
                    key: key,
                    'max-duration': 600,
                    maxRetries: 2,
                    sauceConfig: {
                        'idle-timeout': 600,
                        commandTimeout: 600,
                        idleTimeout: 600,
                        maxDuration: 600,
                        recordVideo: false
                    },
                    statusCheckAttempts: -1,
                    testname: name,
                    throttled: 6,
                    tunnelArgs: [],
                    tunnelTimeout: 600,
                    urls: urls,
                    username: username
                }
            }
        },
        watch: {}
    });

    // Load dependencies
    for (var key in grunt.file.readJSON('package.json').devDependencies) {
        if (key !== 'grunt' && key.indexOf('grunt') === 0) {
            grunt.loadNpmTasks(key);
        }
    }

    grunt.registerTask('dev', [ 'connect', 'watch' ]);
    grunt.registerTask('test', [ 'connect', 'saucelabs-mocha' ]);
};
