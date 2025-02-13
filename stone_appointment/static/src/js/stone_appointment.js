/** @odoo-module **/

import {ReCaptcha} from "@google_recaptcha/js/recaptcha";
import publicWidget from "@web/legacy/js/public/public_widget";
import { _t } from "@web/core/l10n/translation";
import { post } from "@web/core/network/http_service";
import { useBus, useService } from "@web/core/utils/hooks";

publicWidget.registry.ReservationsAppointment = publicWidget.Widget.extend({
    selector: '.form_reservations_appointment', // !compatibility
    events: {
        'change .s_select_package': 'onChangeViewPackage',
        'click .s_btn_index': 'onClickViewValidateIndex',
        'click .s_btn_next_extras': 'onClickViewValidateExtras',
        'click .s_btn_next_dates': 'onClickViewValidateEvent',
        'click .s_btn_clear_reservation': 'onClickViewClearReservation',
    },
    duration: 350,

    /**
     * @constructor
     */
    init: function () {
        this._super(...arguments);
        this._visibilityFunctionByFieldName = new Map();
        this._visibilityFunctionByFieldEl = new Map();
        this.__started = new Promise(resolve => this.__startResolve = resolve);
        this.orm = this.bindService("orm");
        this.rpc = this.bindService("rpc");
        this.notification = this.bindService("notification");
    },
    willStart: async function () {
        const res = this._super(...arguments);
        this.preFillValues = {};
        $("#package_id").trigger("change");
        return res;
    },

    onViewNotification: async function(message){
        this.notification.add(message, {
            type: "danger",
            title: _t("Error"),
            sticky: true
        });
    },
    onClickViewClearReservation: async function (ev) {
        ev.preventDefault();
        const elem = ev.currentTarget;
        const resultCancel = await this.rpc("/web/reservation/cancel", {});
        if (resultCancel.redirect_url) {
            document.location = encodeURI(resultCancel.redirect_url);
            return true;
        }
    },
    onChangeViewPackage: async function (ev) {
        ev.preventDefault();
        const elem = ev.currentTarget;
        var package_id = $("#package_id option:selected").val();
        if(package_id){
            function format(item) { return item.text; }
            const resultSlots = await this.rpc("/web/reservation/slots", {
                package_id: package_id,
            });
            if (resultSlots) {
                $("#slot_dates").select2({
                    data: resultSlots,
                    formatSelection: format,
                    formatResult: format,
                    placeholder: "Select a date",
                    allowClear: true
                });
                return true;
            }
        }
        return true;
    },
    onClickViewValidateIndex: async function(ev){
        ev.preventDefault();
        var package_id = $("#package_id option:selected").val();
        var recurso_id = $("#recurso_id option:selected").val();
        var date_stop = $("#date_stop").val();
        var date_start = $("#date_start").val();
        var internal_note = $("#internal_note").val();
        if(package_id == '-1' || package_id == -1){
            this.onViewNotification("Please select a package");
            return false;
        }
        if(recurso_id == '-1' || recurso_id == -1){
            this.onViewNotification("Please select a resource");
            return false;
        }
        var slotValue = this.$('#slot_dates').select2('data');
        if(slotValue){
            if(slotValue.id){
                console.log("---------- slotValueTEXT", slotValue.text)
            }else{
                this.onViewNotification("Please select the start date");
                return false;
            }
        }
        const updateSaleOrder = await this.rpc("/stn_reservation/extra", {
            package_id: package_id,
            recurso_id: recurso_id,
            date_start: slotValue.id,
            date_stop: date_stop,
            internal_note: internal_note
        });
        if (updateSaleOrder.force_refresh) {
            document.location = encodeURI(updateSaleOrder.redirect_url);
        }else {
            var url_href = '/web/reservation';
            document.location = encodeURI(url_href);
        }
        return true;
    },
    onClickViewValidateExtras: async function(ev){
        ev.preventDefault();
        var package_id = $("#package_id").val();
        var recurso_id = $("#recurso_id").val();
        var date_start = $("#date_start").val();
        var date_stop = $("#date_stop").val();
        var internal_note = $("#internal_note").val();
        var guides = $("#guides").val();
        var option_id = $("#option_id option:selected").val();
        var guest_ids = $("[name='guest_id[]']").toArray().map(item => parseInt(item.value));
        let commonUrlParams = new URLSearchParams(window.location.search);

        console.log("---- date_start", date_start);

        var additional_fees = [];
        var additional_fees_ids = JSON.parse($("#additional_fees_ids").val());
        for (const fees of additional_fees_ids) {
            var int_af = $("#int_af_"+fees).val() || '0';
            additional_fees.push({
                additional_fees_id: fees,
                extra: Number(int_af)
            });
        }
        if(option_id == '-1' || option_id == -1){
            this.onViewNotification("Please select an option");
            return false;
        }
        if(guides != null && Number(guides) < 0.0){
            this.onViewNotification("Please select the number of guides");
            return false;
        }
        // if(guides == null || guides == ""){
        //     this.onViewNotification("Please select the number of guides");
        //     return false;
        // }
        if (guest_ids.length === 0){
            this.onViewNotification("Please select attendees");
            return false;
        }
        if(package_id != '-1' || package_id != -1){
            const updateSaleOrder = await this.rpc("/web/reservation/sale/lines", {
                package_id: package_id,
                recurso_id: recurso_id,
                date_start: date_start,
                date_stop: date_stop,
                option_id: option_id,
                guest_ids: guest_ids,
                int_guides: guides,
                additional_fees: additional_fees,
                internal_note: internal_note
            });
            if (updateSaleOrder.error) {
                this.onViewNotification(updateSaleOrder.error);
                return false;
            }else {
                var url_href = '/web/reservation/extra?'+commonUrlParams.toString();
                document.location = encodeURI(url_href);             
                //const updateSaleOrder = await this.rpc("/web/reservation/sale/validate", {});
            }
            return;
        }
    },
    onClickViewValidateEvent: async function(ev){
        ev.preventDefault();
        let commonUrlParams = new URLSearchParams(window.location.search);
        var package_id = $("#package_id").val();
        var recurso_id = $("#recurso_id").val();
        var date_start = $("#date_start").val();
        var date_stop = $("#date_stop").val();
        if(package_id != '-1' || package_id != -1){
            const content = await this.rpc("/web/reservation/comfirm", {
                package_id: package_id,
                recurso_id: recurso_id,
                date_start: date_start,
                date_stop: date_stop
            });
        }
        var url_href = '/web/reservation/viewcomfirm?'+commonUrlParams.toString();
        document.location = encodeURI(url_href);
        return;
    },

})

