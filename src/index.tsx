import { staticClasses } from "@decky/ui";
import { definePlugin } from "@decky/api";
import { GiPlasticDuck } from "react-icons/gi";
import { Content } from "./components/Content";

export default definePlugin(() => {
  console.log("decky-lsfg-vk-arm64 plugin initializing");

  return {
    name: "LSFG-VK ARM64",
    titleView: <div className={staticClasses.Title}>LSFG-VK ARM64</div>,
    alwaysRender: true,
    content: <Content />,
    icon: <GiPlasticDuck />,
    onDismount() {
      console.log("decky-lsfg-vk-arm64 unloading");
    }
  };
});
