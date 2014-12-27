import os
import bpy
from bpy_extras.io_utils import path_reference
from .tools import safe_query_selector_id

BLENDER2XML_MATERIAL = "(diffuseColor, specularColor, shininess, ambientIntensity, transparency) = xflow.blenderMaterial(diffuse_color, diffuse_intensity, specular_color, specular_intensity, specular_hardness, alpha)"

TEXTURE_EXTENSION_MAP = dict(REPEAT="repeat", EXTEND="clamp")


class Material:
    context = None
    id = ""
    script = "urn:xml3d:shader:phong"
    data = None
    compute = BLENDER2XML_MATERIAL
    dir = None
    copy_set = set()

    def __init__(self, name, context, path):
        self.id = name
        self.context = context
        self.path = path
        self.data = []

    @staticmethod
    def from_blender_material(material, context, path):
        material_id = safe_query_selector_id(material.name)
        mat = Material(material_id, context, path)
        mat.from_material(material)
        return mat

    def from_material(self, material):
        data = self.data
        data.append({"type": "float", "name": "diffuse_intensity",
                     "value": material.diffuse_intensity})
        data.append({"type": "float3", "name": "diffuse_color",
                     "value": [tuple(material.diffuse_color)]})
        data.append({"type": "float", "name": "specular_intensity",
                     "value": material.specular_intensity})
        data.append({"type": "float3", "name": "specular_color",
                     "value": [tuple(material.specular_color)]})
        data.append({"type": "float", "name": "specular_hardness",
                     "value": material.specular_hardness})
        data.append(
            {"type": "float", "name": "ambient", "value": material.ambient})

        if material.use_transparency:
            data.append({"type": "float", "name": "alpha", "value": material.alpha})
        else:
            data.append({"type": "float", "name": "alpha", "value": 1})


        # if material.use_face_texture:
        # print("Warning: Material '%s' uses 'Face Textures', which are not (yet) supported. Skipping texture..." % materialName)
        # return

        for texture_index, texture_slot in enumerate(material.texture_slots):
            if not material.use_textures[texture_index] or texture_slot is None:
                continue

            # TODO: Support uses of textures other than diffuse
            if not texture_slot.use_map_color_diffuse or texture_slot.diffuse_color_factor < 0.0001:
                # print("No use")
                continue

            if texture_slot.texture_coords != 'UV':
                self.context.warning(
                    u"Texture '{0:s}' of material '{1:s}' uses '{2:s}' mapping, which is not (yet) supported. Dropped Texture."
                    .format(texture_slot.name, material.name, texture_slot.texture_coords), "texture", 5)
                continue

            texture = texture_slot.texture
            if texture.type != 'IMAGE':
                self.context.warning(
                    "Warning: Texture '%s' of material '%s' is of type '%s' which is not (yet) supported. Dropped Texture."
                    % (texture_slot.name, material.name, texture.type), "texture")
                continue

            image_src = export_image(texture.image, self.path, self.context)

            if texture.extension in {'REPEAT', 'EXTEND'}:
                wrap = TEXTURE_EXTENSION_MAP[texture.extension]
            else:
                wrap = None
                self.context.warning(
                    u"Texture '{0:s}' of material '{1:s}' has extension '{2:s}' which is not (yet) supported. Using default 'Extend' instead..."
                    .format(texture_slot.name, material.name, texture.extension), "texture")

            if image_src:
                # TODO: extension/clamp, filtering, sampling parameters
                # FEATURE: Resize / convert / optimize texture
                data.append(
                    {"type": "texture", "name": "diffuseTexture", "wrap": wrap, "value": image_src})

DefaultMaterial = Material("defaultMaterial", None, None)
DefaultMaterial.data = [{"type": "float3", "name": "diffuseColor", "value": "0.8 0.8 0.8"}, {"type": "float3", "name": "specularColor", "value": "1.0 1.0 0.1"}, {"type": "float", "name": "ambientIntensity", "value": "0.5"}]


def export_image(image, path, context):
    if image.source not in {'FILE', 'VIDEO'}:
        context.warning(u"Image '{0:s}' is of source '{1:s}' which is not (yet) supported. Using default ...".format(image.name, image.source), "texture")
        return None

    if image.packed_file:
        image_data = image.packed_file.data
        image_src = os.path.join("textures", image.name)
        file_path = os.path.join(path, image_src)
        if not os.path.exists(file_path):
            with open(file_path, "wb") as image_file:
                image_file.write(image_data)
                image_file.close()

        # TODO: Optionally pack images base 64 encoded
        # mime_type = "image/png"
        # image_data = base64.b64encode(image.packed_file.data).decode("utf-8")
        # image_src = "data:%s;base64,%s" % (mime_type, image_data)
    else:
        base_src = os.path.dirname(bpy.data.filepath)
        filepath_full = bpy.path.abspath(image.filepath, library=image.library)
        image_src = path_reference(filepath_full, base_src, path, 'COPY', "textures", context.copy_set, image.library)

        # print("image", image_src, image.filepath, self._copy_set)
        image_src = image_src.replace('\\', '/')

    return image_src
