import tempfile

from django.db import models
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from pdf2image import convert_from_path


class UploadedImage(models.Model):
    image = models.ImageField(upload_to='uploaded_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    # can contain other fields like assessment_id, upload_id, etc.

    def __str__(self):
        return f"Image {self.id} uploaded at {self.uploaded_at}"


class PDFUploadSerializer(serializers.Serializer):
    file = serializers.FileField(required=True)


class PDFToImagesUploadView(APIView):
    class_serializer = PDFUploadSerializer

    def post(self, request, *args, **kwargs):
        serializer = self.class_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        pdf_file = serializer.validated_data['file']

        # Save PDF to a temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
            for chunk in pdf_file.chunks():
                temp_pdf.write(chunk)

            temp_pdf_path = temp_pdf.name

            # Convert PDF to images
            images = convert_from_path(temp_pdf_path, dpi=200)

        # Example: Save image URLs as pseudo Django models
        uploaded_image_objs = []
        other_fields = {}  # other_fields can contain assessment_id, upload_id, etc.

        for image in images:
            uploaded_image = UploadedImage.objects.create(image=image, **other_fields)
            uploaded_image_objs.append(uploaded_image)

        UploadedImage.objects.bulk_create(uploaded_image_objs)

        return Response(status=status.HTTP_200_OK)
