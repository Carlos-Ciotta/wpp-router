HANDLERS = {
    # svc = service, p = payload
    "send_text": lambda svc, p: svc.send_text_message(
        to=p.get("to"), text=p.get("text")
    ),
    "send_video": lambda svc, p: svc.send_video_message(
        to=p.get("to"),
        video_url=p.get("video_url"),
        caption=p.get("caption")
    ),
    "send_document": lambda svc, p: svc.send_document_message(
        to=p.get("to"),
        document_url=p.get("document_url"),
        caption=p.get("caption"),
        filename=p.get("filename")
    ),
    "send_audio": lambda svc, p: svc.send_audio_message(
        to=p.get("to"),
        audio_url=p.get("audio_url"),
        caption=p.get("caption")
    ),
    "send_image": lambda svc, p: svc.send_image_message(
        to=p.get("to"),
        image_url=p.get("image_url"),
        caption=p.get("caption")
    ),
    "send_interactive": lambda svc, p: svc.send_interactive_message(
        to=p.get("to"),
        header=p.get("header"),
        body=p.get("body"),
        footer=p.get("footer"),
        buttons=p.get("buttons")
    ),
    "send_list": lambda svc, p: svc.send_list_message(
        to=p.get("to"),
        header=p.get("header"),
        body=p.get("body"),
        footer=p.get("footer"),
        button_text=p.get("button_text"),
        sections=p.get("sections")
    ),
    "send_template": lambda svc, p: svc.send_template_message(
        to=p.get("to"),
        template_name=p.get("template_name"),
        language_code=p.get("language_code", "pt_BR"),
        components=p.get("components")
    ),
    "get_messages": lambda svc, p: svc.get_messages_by_phone(
        phone=p.get("phone"),
        limit=p.get("limit", 50),
        skip=p.get("skip", 0)
    ),
}
