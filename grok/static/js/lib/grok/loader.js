/* ----------------------------------------------------------------------
 * Numenta Platform for Intelligent Computing (NuPIC)
 * Copyright (C) 2015, Numenta, Inc.  Unless you have purchased from
 * Numenta, Inc. a separate commercial license for this software code, the
 * following terms and conditions apply:
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 3 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
 * See the GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see http://www.gnu.org/licenses.
 *
 * http://numenta.org/licenses/
 * ---------------------------------------------------------------------- */

/*
 * This module assumes jQuery ($), Underscore (_), and LAB.js ($LAB).
 */

(function() {

    if (! window.YOMPUI) {
        window.YOMPUI = {};
    }

    /*************************************************************************
     * IMPORTANT!
     * Hyde (http://hyde.YOMPhub.com) has a problem processing the regular
     * expressions in this file because they contain double curly braces, which
     * hyde uses to identify string tokens. To prevent this problem, all double
     * curly braces have been split apart by string concatenation within the
     * code, and by a single white space character within code comments.
     *************************************************************************/

    var tokenRegex = new RegExp('{' + '{([^}]*)}' + '}', 'g'),
        head = document.getElementsByTagName('head')[0],
        body = document.getElementsByTagName('body')[0];

    /**
     * Recursively looks through an object given an array of keys that define
     * hierarchical node names, and returns the value represented by the keys
     * array within the object.
     * @param obj {Object} to search
     * @param keys {Array} hierarchical keys representing a depth search within
     * the object
     * @return {Object}
     */
    function extractObjectValueByKeyArray(obj, keys) {
        if (keys.length === 1) {
            return obj[keys[0]]
        } else {
            return extractObjectValueByKeyArray(obj[keys.shift()], keys)
        }
    }

    /**
     * Injects any values matching certain string tokens into a string. For
     * example, if
     *  str="Hello, { {person.name} }!! How is your { {animal} }?"
     *  vals={person:{name:'Person'},animal:"WildAnimal"}
     * This function would return:
     *  "Hello, Person!! How is your WildAnimal?"
     * @param str {String} Any tokens within string will be substituted if
     * values exist within the vals object.
     * @param vals {Object} the substitutions to make into the string
     * @return {String} reconstructed input string with substitutions make.
     */
    function injectMessageValues(str, vals) {
        return str.replace(tokenRegex, function(word, term) {
            return extractObjectValueByKeyArray(vals, term.split('.'));
        });
    }

    /**
     * Helper function for YOMPUI.msgs. Used to inject an object full of data
     * into any strings contained in an object.
     * @param value {Object} the msgs object
     * @param sub {Object} The substitutions
     * @return {Object} Results of the substitution.
     */
    function constructMessage(value, sub) {
        var result = {};
        if (typeof value === 'string') {
            // if string, process string
            if (value.search('{' + '{.*}' + '}') >= 0) {
                // if there are tokens to replace, replace them
                result = injectMessageValues(value, sub);
            } else {
                // else the result is just the string
                result = value;
            }
        } else if (Object.prototype.toString.call(value) === '[object Array]') {
            result = [];
            // if array, recursively processes array values
            value.forEach(function(item) {
                result.push(constructMessage(item, sub));
            });
        } else {
            // assume everything else is just an object
            Object.keys(value).forEach(function(innerKey) {
                result[innerKey] = constructMessage(value[innerKey], sub);
            });
        }
        return result;
    }

    /**
     * We're going to do something interesting here, that JavaScript lets us.
     * We're defining a function call YOMPUI.msgs, which will also act as a
     * key-value store for messages. Users will use it like this:
     *  YOMPUI.msgs('msg-key') // to return a raw msgs object for a template
     * Or:
     *  YOMPUI.msgs('msg-key', {user: {firstName: 'Steve'}}
     *
     * This way, users can inject values into their messages easily, without
     * calling another function. If there are any string values that contain
     * the token { {user.firstName} }, YOMPUI.msgs will replace that value with
     * the subs object given.
     *
     * It can also be used directly as a key-value store:
     *  YOMPUI.msgs['msg-key']
     * But of course, no substitutions can be made this way.
     *
     * @param key
     * @param subs
     * @return {*}
     */
    YOMPUI.msgs = function(key, subs) {
        if (! subs) {
            return YOMPUI.msgs[key];
        }
        return constructMessage(YOMPUI.msgs[key], subs);
    };

    /**
     * Responsible for all the dynamic loading of JavaScript files, CSS files,
     * HTML templates, and message text used within this application. In
     * addition to loading these resources, it will also instantiate backbone
     * view instances if configured to. Keeps track of duplicate resources and
     * does not load dupes.
     *
     * Uses LABjs for script loading.
     *
     * @param [opts] {Object} Options.
     * @param [opts.namespace] {String} Where to assume constructors are
     * located when instantiating new views.
     * @param [opts.cachePostfix] {String} Attaches a postfix string to all
     * requests for resources to ensure browser caches are not used. This is
     * useful when bumping versions on deployment, where the cachePostFix value
     * includes the version of the client-side application. Used on JavaScript,
     * CSS, and HTML files.
     * @param [opts.dependencies] {Object} Details list of dependencies, loaded
     * up front, so the loader knows where everything is located.
     * @param [opts.contentPaneId] {String} The main content pane ID for the
     * DOM, used when constructing new Backbone views, by giving this element
     * to them by default for their views to render.
     * @constructor
     */
    function Loader(opts) {
        this.namespace = opts.namespace;
        this.cachePostfix = opts.cachePostfix;
        this.deps = opts.dependencies;
        this.contentPaneId = opts.contentPaneId;
        this.loaded = {
            scripts: [],
            css: [],
            templates: [],
            msgs: []
        };
        _.extend(this, Backbone.Events);
    }

    /**
     * Loads specified template with given id.
     * @param src {string} location of the template
     * @param id {string} id of the template, which is used to inject it into the DOM
     * @param fn {function} callback function when done, passed id
     */
    Loader.prototype.loadTemplate = function(src, id, fn) {
        var me = this,
            loadedTemplates = this.loaded.templates;
        if (_.contains(loadedTemplates, id)) {
            // skip already loaded templates, which also prevents reloading
            // msgs for each template
            return fn(null, id);
        }
        if (me.cachePostfix) {
            src += '?' + me.cachePostfix;
        }
        $.ajax({
            url: src,
            success: function(resp) {
                var $script = $('<script type="text/template" id="' + id + '">' + resp + '</script>');
                $(body).append($script);
                loadedTemplates.push(id);
                fn(null, id);
            },
            failure: fn
        });
    };

    /**
     * Manages loading multiple templates asynchronously and calling callback when
     * all are complete.
     * @param opts {Object} Options for loading templates.
     * @param opts.templates {Object} The templates to load, k-v pairing of
     * name to path.
     * @param opts.msgs {Array} Identifiers of any additional messsages to load
     * from server in addition to any that automatically load with template.
     * @param callback
     */
    Loader.prototype.loadTemplates = function(opts, callback) {
        var me = this,
            loaded = 0,
            tmpls,
            numTemplates,
            msgsToLoad = {},
            id, whenDone, error;

        opts = opts || {};
        tmpls = opts.templates || {}
        numTemplates = Object.keys(tmpls).length;

        whenDone = function(err, doneId) {
            if (err) {
                error = err;
                return callback(err)
            }
            loaded++;
            if (loaded === numTemplates) {
                // only callback when all templates have loaded
                callback(null, doneId);
            }
        };

        if (numTemplates === 0) {
            return callback();
        }

        if (! YOMPUI.preventMessages) {
            // Before loading the templates, load the messages for the templates
            // we require through one batched call. But the tmpls object might have
            // messages that we've already loaded, so we'll do a quick loop over
            // them to make sure we only request msgs we really need.
            _.each(tmpls, function(val, key) {
                if (! _.contains(me.loaded.msgs, key)) {
                    msgsToLoad[key] = val;
                }
            });
        }

        /**
         * Called when messages are loaded.
         */
        function doneLoadingMessages() {
            for (id in tmpls) {
                if (tmpls.hasOwnProperty(id)) {
                    if (! error) {
                        me.loadTemplate(tmpls[id], id, whenDone);
                    }
                }
            }
        }

        // If there are additional msgs to load from server, we'll add them to
        // the same batched request for messages, but with a special key to
        // identify them. They get stored as a comma-delimited field in the
        // request for simplicity.

        if (opts.msgs) {
            msgsToLoad.explicit = opts.msgs.join(',');
        }

        if (Object.keys(msgsToLoad).length > 0) {
            $.ajax({
                url: NTA.baseUrl + '/_msgs',
                data: msgsToLoad,
                type: 'POST',
                success: function(msgs) {
                    // Stash the msgs by template id as a property of the msgs
                    // function defined above, so the function can be used as a
                    // map as well as a lookup/substitution function.
                    Object.keys(msgs).forEach(function(msgKey) {
                        // mix messages over local copy, overriding local values
                        YOMPUI.msgs[msgKey] = msgs[msgKey];
                        me.loaded.msgs.push(msgKey);
                    });
                    doneLoadingMessages();
                },
                failure: callback
            });
        } else {
            doneLoadingMessages();
        }

    };

    /**
     * Loads an array of css file locations into the DOM.
     * @param csses {Array} list of css locations to load
     * @param callback {Function} Called after css links are added to head, NOT
     * after browser has loaded them. So there could be a flash of unstyled
     * content.
     */
    Loader.prototype.loadCss = function(csses, callback) {
        var me = this,
            loadedCss = this.loaded.css;
        if (csses && csses.length) {
            csses.forEach(function(css) {
                if (me.cachePostfix) {
                    css += '?' + me.cachePostfix;
                }
                if (_.contains(loadedCss, css)) {
                    // skip already loaded CSS
                    return;
                }
                var newLink = document.createElement('link');
                newLink.setAttribute('href', css);
                newLink.setAttribute('rel', 'stylesheet');
                newLink.setAttribute('type', 'text/css');
                head.appendChild(newLink);
                me.loaded.css.push(css);
            });
            callback();
        } else {
            callback();
        }
    };

    /**
     * Loads scripts and templates specified, as well as including any resources
     * defined in this.deps.all, which should be included on all pages.
     *
     * @param [opts] {Object} Options for loading resources.
     * @param [opts.templates] {Object} Key-Value pairing of template names to
     * locations.
     * @param [opts.scripts] {Array} List of script locations to load.
     * @param [opts.msgs] {Array} List of message locations to load in addition
     * to any that are already loaded automatically with the templates.
     * @param fn {Function} Called when loading is completed.
     */
    Loader.prototype.loadResources = function(opts, fn) {

        var me = this,
            templates, css, scripts, msgs,
            allTemplatesToLoad;

        opts = opts || {};
        templates = opts.templates;
        css = opts.css;
        scripts = opts.scripts;
        msgs = opts.msgs;

        // mix in all the "all" templates and scripts
        allTemplatesToLoad = _.clone(templates);

        // first load the templates for views
        this.loadTemplates({
            templates: allTemplatesToLoad,
            msgs: msgs
        }, function(err) {
            var i;
            if (err) {
                throw new Error(err);
            }
            if (me.cachePostfix) {
                for (i = 0; i < scripts.length; i++) {
                    scripts[i] = scripts[i] + '?' + me.cachePostfix;
                }
            }
            // load the css after the templates are loaded
            me.loadCss(css, function() {
                // load the scripts after css is loaded.
                // It's assumed that the scripts must be loaded in the proper
                // order, sequentially
                function sequentialScriptLoader() {
                    var next;
                    if (scripts.length) {
                        next = scripts.shift();
                        $LAB.script(next).wait(sequentialScriptLoader);
                    } else {
                        fn();
                        me.trigger('finished');
                    }
                }
                sequentialScriptLoader();
            });
        });
    };

    /**
     * Load resources for a particular entry in the dependency table attached
     * to the Router. Just a helper function.
     */
    Loader.prototype.loadResourcesForPage = function(type, msgs, fn) {
        var pagesOrPanels = 'pages',
            templates, css, scripts;
        if (! this.deps[pagesOrPanels][type]) {
            pagesOrPanels = 'panels';
        }
        templates = this.deps[pagesOrPanels][type].templates;
        css = this.deps[pagesOrPanels][type].css;
        scripts = this.deps[pagesOrPanels][type].scripts;

        this.loadResources({
            templates: templates, css: css, scripts: scripts, msgs: msgs
        }, fn);
    };

    /**
     * Given name of page, loads resources and constructs the page, giving the
     * DOM element corresponding to #content to the View object to render
     * within.
     * @param {string} name Name of the page to load.
     * @param {object} opts Options.
     * @param {object} opts.query Backbone query object from router.
     * @param {Array} [opts.msgs] Any additional messages to load from server.
     * @param {Function} opts.callback Called with newly created view instance
     * after load.
     */
    Loader.prototype.loadAndStart = function(name, opts) {
        opts = opts || {};
        var me = this,
            NS = this.namespace,
            prefix = name.substr(0,1).toUpperCase() + name.substr(1, name.length - 1),
            msgs = opts.msgs,
            viewClassName = opts.viewClassName,
            callback = opts.callback,
            newOptions = opts || {};
        // might be a callback, and we don't want that in newOptions
        delete newOptions.callback;
        delete newOptions.viewClassName;
        delete newOptions.msgs;

        this.loadResourcesForPage(name, msgs, function() {
            var newView;
            newOptions.el = $('#' + me.contentPaneId);
            newView = new NS[(viewClassName || prefix + 'View')](newOptions);
            if (callback) {
                callback(newView);
            }
        });
    };

    YOMPUI.Loader = Loader;

})();
