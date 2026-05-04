import { createApp } from "vue";
import App from "./App.vue";
import router from "./router";
import "./assets/government-ui.css";
import "./assets/dm-dark-theme-overrides.css";

createApp(App).use(router).mount("#app");

