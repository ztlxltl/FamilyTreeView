# Badge Development Guide

You can create custom badges to highlight certain people or families or to display additional information about them. Below are the steps to create a Gramps addon that implements a new badge are explained. Please familiarize yourself with Gramps' addon system and the API to retrieve information from the database to provide the badge content you want.

Note that the interface is likely to change. If you develop a working addon now and it breaks with a future update of FamilyTreeView (or Gramps), come back to this guide and check for changes.

## Important

By developing or using an addon, including a badge addon, you are responsible for any errors or problems caused by the addon, including but not limited to crashing Gramps, data loss, or data corruption caused directly or indirectly by the addon. Make backups before developing a badge addon or testing a badge addon created by someone else. 

## 1. Find your Gramps user directory and create a new folder for your addon

This is explained in the [Gramps Wiki](https://www.gramps-project.org/wiki/index.php/Gramps_5.2_Wiki_Manual_-_User_Directory) and in the [README file](../README.md#downloading-the-source-code). In the `gramps52/plugins` subdirectory, create a new folder for your addon, e.g. `MyCustomBadge`. The directory name should be unique to your addon.

## 2. Create a `.gpr.py` file (Gramps Plugin Registration file)

Create a Gramps Plugin Registration file in this new directory. It should have a structure similar to the following:

```py
register(GENERAL,
    id = "my_custom_badge",
    name = _("My custom badge"),
    description = _("My custom badge for FamilyTreeView"),
    category = "family_tree_view_badge_addon",
    version = '0.1.0',
    gramps_target_version = "6.0",
    status = STABLE,
    fname = "my_custom_badge.py",
    authors = ["My Name"],
    authors_email = ["my.name@example.com"],
    load_on_reg = True,
)
```

- **`GENERAL`** is the addon type. It must be `GENERAL` for your badge addon to be able to be found by FamilyTreeView. 
- `id` a unique ID for your addon. If the name is too general for a badge addon and there is a risk that the name will conflict with other addons, you can add `badge`(`s`) and/or `family_tree_view` to distinguish it from other addons.
- `name` the name of your addon
- `description` a description of your addon. It should make it clear that the badges are meant to be used with FamilyTreeView, so that others will know that if they don't know the context of your addon or badges in general.
- **`category`** must be `"family_tree_view_badge_addon"` for your badge addon to be found by FamilyTreeView
- `version` the version of your addon
- `status` the status of your addon, `UNSTABLE`, `EXPERIMENTA`, `BETA` or `STABLE`
- `fname` the file name where the badges are defined, see next step
- `author` the list of the names of the authors
- `author_email` the list of the authors' emails in the same order as in `authors`
- **`load_on_reg`** must be set to `True` so your addon can pass the registration function to Gramps

The important items in the list above are in bold.

Incrementing the `version` number after changes, setting the correct `status` and providing `author` information (including `author_email`) is important if you want to distribute your badge addon. There is currently no recommended way to do this. (Gramps' addon-source repository is not recommended, as FamilyTreeView itself is not (yet) included there). This document will be updated when there is a recommended way for distribution.

## 3. Create a python file where the badge is defined

Create a `.py` file in the same directory. It should have the name you specified in the `.gpr.py` file, e.g. `my_custom_badge.py`. The new must define a function called `load_on_reg` that takes three arguments and returns a function or a list of functions. These functions must take three input arguments and must call FamilyTreeView's badge registration method.
There are three badge registration methods:

- `register_badges_callbacks(badge_id, badge_name, person_badge_callback, family_badge_callback)` to register both, person and family badges
- `register_person_badges_callback(badge_id, badge_name, person_badge_callback)` to register person badges
- `register_family_badges_callback(badge_id, badge_name, family_badge_callback)` to register family badges

The first two input arguments are a unique badge ID and a badge name. The callbacks are called for each person or family and should return the information about the badge to be added to the tree.

Below is a very basic example of a badge addon. Note that the value returned by the callback is constant in this case. You can write code to adapt the returned value to the person or family, e.g. different text, color etc.

```py
def load_on_reg(dbstate, uistate, addon):
    return register_badge

def register_badge(dbstate, uistate, badge_manager):
    badge_manager.register_person_badges_callback(
        "my_custom_badge", "My custom badge",
        cb_create_person_badge
    )

def cb_create_person_badge(dbstate, uistate, person_handle):
    return [
        {
            "background_color": "red",
            "content": [
                {
                    "content_type": "text",
                    "text": "test"
                }
            ]
        }
    ]
```

All badges registered with a call to one of the registration methods can be activated and deactivated together (but separately for person and family badges). You can call these methods multiple times if multiple badges should be individually activatable or provide multiple badges in one callback to make them activate together.

The callback function(s) passed to the registration methods take three arguments: Gramps' dbstate, Gramps' uistate and the handle of the person or family whose badge is requested by FamilyTreeView. This callback is called for each person or family visible in the tree. Therefore, the callback function should return the result quickly. Otherwise, the user may have to wait for all the badges to be generated and the tree may appear with a delay.

The callback returns a list of dicts. If no badge should be displayed for a person or family, an empty list can be returned. If multiple badges are to be displayed for a person or family, the list can have multiple dicts.

Each dict defines one badge. There are required and optional keys for the badge:
- `background_color` (`str` required): The background color of the badge, as a color name or a hexadecimal RBG triplet.
- `content` (`list` of `dict`s, required): The content of the badge, see below.
- `stroke_color` (`str`, optional): The stroke color of the badge, as a color name or a hexadecimal RBG triplet. Defaults to black.
- `click_callback` (`callable`, optional): The callback that is called when the user clicks the badge. Defaults to no callback.
- `tooltip` (`str`, optional): The tooltip for the badge.

You can have multiple content elements in the `content` list. Each element is a dict with the `content_type` key and content type specific keys. The following content types are currently supported:
- `text`: A string that is added to the Badge.
  Content specific keys:
  - `text` (`str`, required): The text to show.
  - `text_color` (`str`, optional): The color of the text, as a color name or a hexadecimal RBG triplet. Defaults to black.
  - `tooltip` (`str`, optional): The tooltip for the badge.
- `icon_file_svg`: An svg file.
  Content specific keys:
  - `file` (`str`): The path pointing to the svg file. The svg tag should have a valid viewBox property.
  - `current_color` (`str`, optional): The color to set the `<svg>`'s `color` CSS property to. It will be used by the svg file for all elements whose color is set to `currentcolor`. For more context, see [MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/color_value#currentcolor_keyword). Defaults to black.
  Note that not all CSS features appear to be supported by pixbuf.
- `icon_svg_data_callback`: A callback to return svg path data string for the given icon size.
  - `callback` (`callable`): The callback taking the maximum width and maximum height of the icon as two arguments and returning the string, the width and the height of the icon. Note that this is still experimental and the callback's signature can change in the future.
  - `fill_color` (`str`, optional): The fill color. Defaults to black.
  - `stroke_color` (`str`, optional): The fill color. Defaults to no color.
  - `line_width` (`int`, optional): The fill color. Defaults to 0.


## 4. Test the badge

Save the files, open or re-open Gramps and switch to FamilyTreeView. The badges should appear.
