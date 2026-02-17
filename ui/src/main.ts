import './style.css';

import Aura from '@primeuix/themes/aura';
import Button from 'primevue/button';
import Card from 'primevue/card';
import Chart from 'primevue/chart';
import Column from 'primevue/column';
import PrimeVue from 'primevue/config';
import DataTable from 'primevue/datatable';
import Dialog from 'primevue/dialog';
import InputNumber from 'primevue/inputnumber';
import InputText from 'primevue/inputtext';
import Select from 'primevue/select';
import SelectButton from 'primevue/selectbutton';
import Tag from 'primevue/tag';
import Textarea from 'primevue/textarea';
import Toast from 'primevue/toast';
import ToastService from 'primevue/toastservice';
import Tooltip from 'primevue/tooltip';
import { createApp } from 'vue';

import App from '@/App.vue';
import { router } from '@/router';

const app = createApp(App);

app.use(PrimeVue, {
    theme: {
        preset: Aura,
    },
});
app.use(ToastService);
app.use(router);

app.component('AppButton', Button);
app.component('AppCard', Card);
app.component('AppChart', Chart);
app.component('AppColumn', Column);
app.component('AppDataTable', DataTable);
app.component('AppDialog', Dialog);
app.component('AppInputNumber', InputNumber);
app.component('AppInputText', InputText);
app.component('AppSelect', Select);
app.component('AppSelectButton', SelectButton);
app.component('AppTag', Tag);
app.component('AppTextarea', Textarea);
app.component('AppToast', Toast);

app.directive('tooltip', Tooltip);

app.mount('#app');
