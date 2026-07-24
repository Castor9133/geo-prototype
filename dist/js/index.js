/**
 * GEOrank 首页：Suite 导向工作台（公司目录已下线）。
 */
(function () {
    'use strict';

    const run = window.GEOrankCommon?.PageLifecycle?.run?.bind(window.GEOrankCommon.PageLifecycle)
        || ((callback) => callback());

    run(() => {
        if (window.GEOrankCommon?.Layout) {
            window.GEOrankCommon.Layout.init();
        }
    });
})();
