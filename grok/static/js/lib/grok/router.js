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
 * START HERE!! See the YOMPUI.Router definition below.
 */

(function() {

    var initializer,
        routerExtension;

    initializer = function() {
        YOMPUI.loader = this.loader = new YOMPUI.Loader({
            namespace: YOMPUI,
            cachePostfix: ['v', YOMPUI.product.version].join('='),
            dependencies: YOMPUI.Router.prototype.deps,
            contentPaneId: 'content'
        });
        // allows users to provide their own initialize functions
        if (this.initializer) {
            this.initializer.apply(this, arguments);
        }
    };

    // creating the object to extend the Backbone router, and allowing the
    // application to provide its own details through YOMPUI.routes.
    routerExtension = {
        routes: YOMPUI.routes.urls,
        deps: YOMPUI.routes.deps,
        initialize: initializer
    };
    // mixing in the handler functions
    Object.keys(YOMPUI.routes.handlers).forEach(function(handlerName) {
        routerExtension[handlerName] = YOMPUI.routes.handlers[handlerName];
    });
    // also add the initializer at the same level as the handlers
    routerExtension.initializer = YOMPUI.routes.initialize;

    /**
     * This router is the starting point for the YOMP SITE!
     */
    YOMPUI.Router = Backbone.Router.extend(routerExtension);

})();
