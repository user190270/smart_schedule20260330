import { createApp } from "vue";
import {
  Button,
  Cell,
  CellGroup,
  ConfigProvider,
  Dialog,
  Divider,
  Empty,
  Field,
  Form,
  Icon,
  Loading,
  NavBar,
  Notify,
  Popup,
  Skeleton,
  Tab,
  Tabbar,
  TabbarItem,
  Tabs,
  Tag
} from "vant";
import "vant/lib/index.css";

import App from "./App.vue";
import { router } from "./router";
import { pinia } from "./stores/pinia";
import "./style.css";

const app = createApp(App);

app.use(pinia);
app.use(router);
app.use(ConfigProvider);
app.use(NavBar);
app.use(Button);
app.use(CellGroup);
app.use(Cell);
app.use(Tabbar);
app.use(TabbarItem);
app.use(Tag);
app.use(Notify);
app.use(Form);
app.use(Field);
app.use(Popup);
app.use(Empty);
app.use(Divider);
app.use(Icon);
app.use(Loading);
app.use(Dialog);
app.use(Tabs);
app.use(Tab);
app.use(Skeleton);

app.mount("#app");
