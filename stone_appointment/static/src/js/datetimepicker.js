/** @odoo-module **/

import { deserializeDateTime } from "@web/core/l10n/dates";
import publicWidget from "@web/legacy/js/public/public_widget";
const { DateTime } = luxon;

publicWidget.registry.StoneAppoimentDateTimeWidget = publicWidget.Widget.extend({
    //--------------------------------------------------------------------------
    // Widget
    //--------------------------------------------------------------------------
    selector: 'input[name="datetime_filter"]',
    events: {
        'change .oe_datepicker_root': 'onChangeViewDateTime',
    },

    /**
     * @override
     */
    init: function (parent, params) {
        this._super.apply(this, arguments);
        this.timer = params.timer;
        this.timeLimitMinutes = params.timeLimitMinutes;
        this.surveyTimerInterval = null;
        this.timeDifference = null;
        if (params.serverTime) {
            this.timeDifference = DateTime.utc().diff(
                deserializeDateTime(params.serverTime)
            ).milliseconds;
        }
    },
    /**
    * Two responsabilities : Validate that time limit is not exceeded and Run timer otherwise.
    * If end-user's clock OR the system clock  is de-synchronized before the survey is started, we apply the
    * difference in timer (if time difference is more than 5 seconds) so that we can
    * display the 'absolute' counter
    *
    * @override
    */
    start: function () {
        var self = this;
        const res = this._super(...arguments);

        $(document).on('click', '.o_datetime_picker .o_datetime_buttons .btn-primary', function() {
            console.log("Botón de confirmación clicado");
            const $input = self.$el;
            if ($input.val()) {
                $input.closest('form').submit();
            }
        });
        return res;
    },

    onChangeViewDateTime: async function (ev) {
        ev.preventDefault();
        const elem = ev.currentTarget;
        console.log("-------element ", elem);
    },

});

export default publicWidget.registry.StoneAppoimentDateTimeWidget;